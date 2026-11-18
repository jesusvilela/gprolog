// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Same external diagnostic for immutable Generation 18 and rejected Gen19.
//! Records *all Rust allocator requests made during solve()* only.
//! Counts are not peak RSS, bytes physically copied or causal time attribution.
use std::alloc::{GlobalAlloc, Layout, System};
use std::env;
use std::fs;
use std::hint::black_box;
use std::process;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};

use gprolog_native::{parse_program, parse_query, solve, Limits};
use gprolog_native::engine::{
    clear_choicepoint_profile, read_choicepoint_profile, ChoicepointProfile,
};

struct TraceAllocator;
#[global_allocator]
static ALLOCATOR: TraceAllocator = TraceAllocator;

static ACTIVE: AtomicBool = AtomicBool::new(false);
static ALLOC_CALLS: AtomicU64 = AtomicU64::new(0);
static ALLOC_ZEROED_CALLS: AtomicU64 = AtomicU64::new(0);
static ALLOC_BYTES: AtomicU64 = AtomicU64::new(0);
static REALLOC_CALLS: AtomicU64 = AtomicU64::new(0);
static REALLOC_OLD_BYTES: AtomicU64 = AtomicU64::new(0);
static REALLOC_NEW_BYTES: AtomicU64 = AtomicU64::new(0);
static DEALLOC_CALLS: AtomicU64 = AtomicU64::new(0);
static DEALLOC_BYTES: AtomicU64 = AtomicU64::new(0);

// Atomic-only bookkeeping cannot recurse into the Rust allocator.
// System remains responsible for the real allocation/deallocation.
unsafe impl GlobalAlloc for TraceAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc(layout);
        if !ptr.is_null() && ACTIVE.load(Ordering::Relaxed) {
            ALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
            ALLOC_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        ptr
    }

    unsafe fn alloc_zeroed(&self, layout: Layout) -> *mut u8 {
        let ptr = System.alloc_zeroed(layout);
        if !ptr.is_null() && ACTIVE.load(Ordering::Relaxed) {
            ALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
            ALLOC_ZEROED_CALLS.fetch_add(1, Ordering::Relaxed);
            ALLOC_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        ptr
    }

    unsafe fn realloc(&self, ptr: *mut u8, old: Layout, new_size: usize) -> *mut u8 {
        let updated = System.realloc(ptr, old, new_size);
        if !updated.is_null() && ACTIVE.load(Ordering::Relaxed) {
            REALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
            REALLOC_OLD_BYTES.fetch_add(old.size() as u64, Ordering::Relaxed);
            REALLOC_NEW_BYTES.fetch_add(new_size as u64, Ordering::Relaxed);
        }
        updated
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        if ACTIVE.load(Ordering::Relaxed) {
            DEALLOC_CALLS.fetch_add(1, Ordering::Relaxed);
            DEALLOC_BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
        }
        System.dealloc(ptr, layout);
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct AllocationRecord {
    alloc_calls: u64,
    alloc_zeroed_calls: u64,
    alloc_requested_bytes: u64,
    realloc_calls: u64,
    realloc_old_requested_bytes: u64,
    realloc_new_requested_bytes: u64,
    dealloc_calls: u64,
    dealloc_layout_bytes: u64,
}

fn reset() {
    ACTIVE.store(false, Ordering::SeqCst);
    for counter in [
        &ALLOC_CALLS, &ALLOC_ZEROED_CALLS, &ALLOC_BYTES,
        &REALLOC_CALLS, &REALLOC_OLD_BYTES, &REALLOC_NEW_BYTES,
        &DEALLOC_CALLS, &DEALLOC_BYTES,
    ] {
        counter.store(0, Ordering::SeqCst);
    }
}

fn snapshot() -> AllocationRecord {
    AllocationRecord {
        alloc_calls: ALLOC_CALLS.load(Ordering::SeqCst),
        alloc_zeroed_calls: ALLOC_ZEROED_CALLS.load(Ordering::SeqCst),
        alloc_requested_bytes: ALLOC_BYTES.load(Ordering::SeqCst),
        realloc_calls: REALLOC_CALLS.load(Ordering::SeqCst),
        realloc_old_requested_bytes: REALLOC_OLD_BYTES.load(Ordering::SeqCst),
        realloc_new_requested_bytes: REALLOC_NEW_BYTES.load(Ordering::SeqCst),
        dealloc_calls: DEALLOC_CALLS.load(Ordering::SeqCst),
        dealloc_layout_bytes: DEALLOC_BYTES.load(Ordering::SeqCst),
    }
}

fn profile_fields(p: &ChoicepointProfile) -> [(&'static str, u64); 18] {
    [
        ("user_predicate_dispatches", p.user_predicate_dispatches),
        ("try_clause_tasks", p.try_clause_tasks),
        ("work_resume_tasks", p.work_resume_tasks),
        ("clause_choices_pushed", p.clause_choices_pushed),
        ("disjunction_choices_pushed", p.disjunction_choices_pushed),
        ("clause_continuation_vectors_cloned", p.clause_continuation_vectors_cloned),
        ("clause_continuation_goals_cloned", p.clause_continuation_goals_cloned),
        ("shared_continuation_anchors", p.shared_continuation_anchors),
        ("shared_continuation_handle_clones", p.shared_continuation_handle_clones),
        ("shared_continuation_fallback_copies", p.shared_continuation_fallback_copies),
        ("resume_suffix_goals_materialized", p.resume_suffix_goals_materialized),
        ("disjunction_rest_goals_cloned", p.disjunction_rest_goals_cloned),
        ("choicepoints_redone", p.choicepoints_redone),
        ("cut_choicepoints_pruned", p.cut_choicepoints_pruned),
        ("binding_writes", p.binding_writes),
        ("binding_undo_writes", p.binding_undo_writes),
        ("maximum_pending_choices", p.maximum_pending_choices as u64),
        ("total_search_steps", p.total_search_steps),
    ]
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    // source.pl primitive-goal. repeats solutions steps warmups samples
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 7 {
        return Err("usage: alloc_probe SOURCE QUERY REPEAT SOLUTIONS STEPS WARMUPS SAMPLES".into());
    }
    let source = fs::read_to_string(&args[0])?;
    let program = parse_program(&source)?;
    let mut query = parse_query(&args[1], program.next_var)?;
    if query.goals.len() != 1 { return Err("query must be one primitive goal".into()); }
    let repeat: usize = args[2].parse()?;
    let solutions: usize = args[3].parse()?;
    let steps: usize = args[4].parse()?;
    let warmups: usize = args[5].parse()?;
    let samples: usize = args[6].parse()?;
    if !(1..=128).contains(&repeat) || !(1..=16).contains(&solutions)
        || steps == 0 || warmups > 20 || !(1..=20).contains(&samples)
    {
        return Err("invalid bounded diagnostic arguments".into());
    }
    query.goals = vec![query.goals[0].clone(); repeat];
    let limits = Limits { max_steps: steps, max_solutions: solutions };
    // Warmups are outside all measurement and source-profile windows.
    for _ in 0..warmups {
        black_box(solve(&program, &query, limits)?);
    }

    let mut expected_answers: Option<String> = None;
    let mut expected_profile: Option<ChoicepointProfile> = None;
    let mut observations = Vec::<AllocationRecord>::with_capacity(samples);
    for _ in 0..samples {
        clear_choicepoint_profile();
        reset();
        ACTIVE.store(true, Ordering::SeqCst);
        let result = black_box(solve(&program, &query, limits));
        ACTIVE.store(false, Ordering::SeqCst);
        // Snapshot and formatting are deliberately outside the tracked span.
        let record = snapshot();
        let profile = read_choicepoint_profile();
        let representation = format!("{:?}", result?);
        if let Some(reference) = &expected_answers {
            if reference != &representation { return Err("intra-probe answer mismatch".into()); }
        } else {
            expected_answers = Some(representation);
        }
        if let Some(reference) = &expected_profile {
            if reference != &profile { return Err("nondeterministic live path counts".into()); }
        } else {
            expected_profile = Some(profile);
        }
        observations.push(record);
    }

    println!("ANSWERS\t{}", expected_answers.expect("at least one sample"));
    for obs in observations {
        println!(
            "ALLOC\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            obs.alloc_calls, obs.alloc_zeroed_calls, obs.alloc_requested_bytes,
            obs.realloc_calls, obs.realloc_old_requested_bytes,
            obs.realloc_new_requested_bytes, obs.dealloc_calls,
            obs.dealloc_layout_bytes
        );
    }
    for (name, count) in profile_fields(&expected_profile.expect("at least one sample")) {
        println!("PROFILE\t{name}\t{count}");
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        process::exit(2);
    }
}
