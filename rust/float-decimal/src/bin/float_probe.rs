// R0 driver: one decimal lexeme per line. Prints OK <bits> or REJECT.
use std::io::{self, BufRead};
use gprolog_float_decimal::finite_decimal_bits;
fn main() {
    for line in io::stdin().lock().lines() {
        let Ok(token) = line else {
            eprintln!("stdin error");
            std::process::exit(2);
        };
        match finite_decimal_bits(&token) {
            Some(bits) => println!("OK {bits:016x}"),
            None => println!("REJECT"),
        }
    }
}
