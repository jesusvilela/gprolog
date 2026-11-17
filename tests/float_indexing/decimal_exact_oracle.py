"""Exact decimal -> binary64 audit: integer-rational oracle vs actual GNU Prolog.

C traces are injected ONLY into throwaway CI source checkouts. Finite inputs
are compared with pre-lexer-guard baseline; unsafe overflow cases are run on
the guarded candidate only. No production C file is changed in Git.
"""
import argparse
from decimal import Decimal
from fractions import Fraction
import hashlib, json, os, random, struct, subprocess, tempfile
from pathlib import Path

SIGN=1<<63
INF=0x7ff0000000000000
TRACE="GPROLOG_DECIMAL_FIDELITY_TRACE"
DIAG="finite floating point literal expected here"
SEED=20261117

def even(n,d):
    q,r=divmod(n,d)
    return q+int(2*r>d or (2*r==d and (q&1)==1))

def rational_bits(v,negative=False):
    if v<0: return rational_bits(-v,not negative)
    n,d=v.numerator,v.denominator
    s=SIGN if negative else 0
    if n==0: return s
    e=n.bit_length()-d.bit_length()
    if (n < (d<<e)) if e>=0 else ((n<<-e)<d): e-=1
    if e>1023: return s|INF
    if e< -1022:
        q=even(n<<1074,d)
        return s|min(q,1<<52)
    shift=52-e
    q=even(n<<shift,d) if shift>=0 else even(n,d<<-shift)
    if q==1<<53: q=1<<52;e+=1
    if e>1023: return s|INF
    return s|((e+1023)<<52)|(q-(1<<52))

def bits(text):
    dec=Decimal(text)
    assert dec.is_finite(), "Never assume NaN/Infinity is a Prolog literal"
    return rational_bits(abs(Fraction(dec)),dec.is_signed())

def exact_decimal(value):
    if value<0: return "-"+exact_decimal(-value)
    n,d=value.numerator,value.denominator
    if n==0: return "0.0"
    a=b=0
    while d%2==0: a+=1;d//=2
    while d%5==0: b+=1;d//=5
    if d!=1: raise ValueError("nonterminating fraction")
    scale=max(a,b)
    raw=str(n*2**(scale-a)*5**(scale-b))
    if len(raw)==1: raw+="0"
    return raw[0]+"."+raw[1:]+"e"+str(len(raw)-1-scale)

def cases():
    maxfinite=(2**53-1)*2**971
    mid=(2**54-1)*2**970
    sub=Fraction(1,2**1074)
    half=sub/2
    normal=Fraction(1,2**1022)
    maxsub=(2**52-1)*sub
    normalmid=(normal+maxsub)/2
    epsilon=Fraction(1,10**800)
    rows=[
      ("zero","0.0"),("negative_zero","-0.0"),
      ("half","0.5"),("half_upper_E","5.000000E-1"),
      ("tenth","0.1"),("tenth_trailing","0.100000000"),
      ("negative_tenth","-0.1"),
      ("max_short","1.7976931348623157e308"),
      ("max_next_decimal","1.7976931348623158e308"),
      ("max_exact",str(maxfinite)+".0"),
      ("overflow_mid_minus1",str(mid-1)+".0"),
      ("overflow_mid_exact",str(mid)+".0"),
      ("overflow_mid_plus1",str(mid+1)+".0"),
      ("overflow_short","1.7976931348623159e308"),
      ("overflow_huge","1.0e309"),
      ("overflow_negative","-1.0e309"),
      ("subnormal_short","5.0e-324"),
      ("subnormal_exact",exact_decimal(sub)),
      ("negative_subnormal",exact_decimal(-sub)),
      ("subhalf_exact",exact_decimal(half)),
      ("subhalf_below",exact_decimal(half-epsilon)),
      ("subhalf_above",exact_decimal(half+epsilon)),
      ("negative_subhalf",exact_decimal(-half)),
      ("negative_subhalf_above",exact_decimal(-half-epsilon)),
      ("max_subnormal",exact_decimal(maxsub)),
      ("normalmid_exact",exact_decimal(normalmid)),
      ("normalmid_below",exact_decimal(normalmid-epsilon)),
      ("normalmid_above",exact_decimal(normalmid+epsilon)),
      ("minnormal_exact",exact_decimal(normal)),
      ("negative_minnormal",exact_decimal(-normal)),
      ("underflow_zero","1.0e-9999"),
      ("negative_underflow_zero","-1.0e-9999")]
    rng=random.Random(SEED)
    for i in range(12):
        k=rng.randrange(1,2**18)
        v=(k*sub if i%3==0 else
           normal+k*sub if i%3==1 else maxsub-k*sub)
        if i&1: v=-v
        rows.append((f"dyadic_seed_{i:02}",exact_decimal(v)))
    return [(name,token,bits(token)) for name,token in rows]

def selftest():
    samples={"0.1":0x3fb999999999999a,"1.0":0x3ff0000000000000,
             "-0.0":SIGN,"5.0e-324":1,
             "1.7976931348623157e308":0x7fefffffffffffff,
             "1.7976931348623159e308":INF}
    for literal,expected in samples.items():
        assert bits(literal)==expected,(literal,hex(bits(literal)))
    assert bits(exact_decimal(Fraction(1,2**1075)))==0
    assert bits(exact_decimal(Fraction(1,2**1075)+Fraction(1,10**800)))==1
    assert bits(str((2**54-1)*2**970)+".0")==INF
    rng=random.Random(SEED)
    for _ in range(120):
        n=rng.randrange(-1000000,1000000);p=rng.randrange(-1080,1050)
        ratio=Fraction(n<<p,1) if p>=0 else Fraction(n,2**-p)
        txt=exact_decimal(ratio)
        wanted=bits(txt)
        try: observed=int.from_bytes(struct.pack(">d",float(txt)),"big")
        except OverflowError: observed=(SIGN if txt.startswith("-") else 0)|INF
        assert wanted==observed,(txt[:30],wanted,observed)
    rows=cases()
    assert len(rows)==44 and sum((n&INF)==INF for _,_,n in rows)==5
    assert max(len(t) for _,t,_ in rows)<1024
    print("PASS: 44 cases, 39 finite, 5 overflow; exact rational self-tests")

def replace_once(src,old,new,expected=1):
    assert src.count(old)==expected,("source anchor drift",src.count(old),old[:95])
    return src.replace(old,new)

def instrument(lexer,parser):
    lex=lexer.read_text()
    old='  if (sscanf(pl_token.name, "%lf", &pl_token.float_num) != 1 ||\n      !(pl_token.float_num <= DBL_MAX && pl_token.float_num >= -DBL_MAX))'
    # Always trace actual C conversion, including a guard rejection.
    body='''  {
    int scanned = sscanf(pl_token.name, "%lf", &pl_token.float_num);
    const char *log_name = getenv("GPROLOG_DECIMAL_FIDELITY_TRACE");
    if (log_name && log_name[0])
      {
        FILE *log = fopen(log_name, "a");
        if (!log) abort();
        fprintf(log, "LEX|%s|%a|%d\\n", pl_token.name, pl_token.float_num,
                scanned == 1 && pl_token.float_num <= DBL_MAX &&
                pl_token.float_num >= -DBL_MAX);
        fclose(log);
      }
'''
    if old in lex:
        lex=replace_once(lex,old,body+'''    if (scanned != 1 ||
        !(pl_token.float_num <= DBL_MAX && pl_token.float_num >= -DBL_MAX))''')
        lex=replace_once(lex,
             '      err_msg = "finite floating point literal expected here";\n    }\n\n push_back:',
             '      err_msg = "finite floating point literal expected here";\n    }\n  }\n\n push_back:')
    else:
        lex=replace_once(lex,'#include <stdlib.h>',
                         '#include <stdlib.h>\n#include <float.h>')
        lex=replace_once(lex,
             '  sscanf(pl_token.name, "%lf", &pl_token.float_num);',
             body+'  }\n')
    lexer.write_text(lex)
    p=parser.read_text()
    p=replace_once(p,'#include <stdio.h>',
                      '#include <stdio.h>\n#include <stdlib.h>')
    logger='''static void
Audit_Float_Term(double x)
{
  const char *path = getenv("GPROLOG_DECIMAL_FIDELITY_TRACE");
  if (path && path[0])
    {
      FILE *f = fopen(path, "a");
      if (!f) abort();
      fprintf(f, "TERM|%a\\n", x);
      fclose(f);
    }
}

'''
    p=replace_once(p,'static StmInf *pstm_i;',logger+'static StmInf *pstm_i;')
    p=replace_once(p,
         '    case TOKEN_FLOAT:\n      term = Pl_Put_Float(pl_token.float_num);',
         '    case TOKEN_FLOAT:\n      Audit_Float_Term(pl_token.float_num);\n      term = Pl_Put_Float(pl_token.float_num);',2)
    p=replace_once(p,'      term = Pl_Put_Float(-pl_token.float_num);',
                     '      Audit_Float_Term(-pl_token.float_num);\n      term = Pl_Put_Float(-pl_token.float_num);')
    parser.write_text(p)
    print("Instrumented throwaway lexer+parser C files; Git sources unchanged")

def execute(cmd,cwd,env,seconds=120):
    try:
        proc=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,text=True,
             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
        return {"code":proc.returncode,"output":proc.stdout[-2800:]}
    except subprocess.TimeoutExpired as e:
        return {"code":None,"output":"TIMEOUT "+repr(e.stdout)[-600:]}

def parse_trace(path):
    if not path.is_file(): return []
    result=[]
    for raw in path.read_text().splitlines():
        parts=raw.split("|")
        if len(parts)==4 and parts[0]=="LEX":
            val=int.from_bytes(struct.pack(">d",float.fromhex(parts[2])),"big")
            result.append({"stage":"LEX","token":parts[1],"bits":f"{val:016x}","finite":parts[3]=="1"})
        elif len(parts)==2 and parts[0]=="TERM":
            val=int.from_bytes(struct.pack(">d",float.fromhex(parts[1])),"big")
            result.append({"stage":"TERM","bits":f"{val:016x}"})
        else: raise RuntimeError("Unexpected C trace: "+raw[:160])
    return result

def check_one(stage,record,token,expected,reject,context,errors):
    traces=record["traces"]
    magnitude=expected & ~SIGN
    lexeme=token.removeprefix("-").replace("E","e")
    lexer=[x for x in traces if x["stage"]=="LEX" and x["token"]==lexeme]
    terms=[x for x in traces if x["stage"]=="TERM"]
    if not lexer: errors.append(context+": missing C lexer trace")
    for x in lexer:
        if int(x["bits"],16)!=magnitude:
            errors.append(context+": lexer rounded different bits "+x["bits"])
        if x["finite"]==reject:
            errors.append(context+": lexer finite/reject flag wrong")
    output=record["command"]["output"]
    if any(s in output.lower() for s in ("segmentation","bad address:","sigsegv")):
        errors.append(context+": fatal process diagnostic")
    if record["command"]["code"] is None:
        errors.append(context+": timed out")
    if reject:
        if terms: errors.append(context+": rejected literal reached Prolog term")
        if DIAG not in output: errors.append(context+": missing controlled lexer error")
        if stage=="compile" and record["command"]["code"]==0:
            errors.append(context+": rejected literal compiled")
    else:
        if not terms: errors.append(context+": missing parser term trace")
        for term in terms:
            if int(term["bits"],16)!=expected:
                errors.append(context+": TERM is not exact oracle bits "+term["bits"])
        if record["command"]["code"]!=0:
            errors.append(context+": finite literal rejected")
        if stage=="consulted" and output.strip()!="OK":
            errors.append(context+": consulted known-answer output wrong "+repr(output[-90:]))

def run_case(name,token,expected,version,bindir,root,errors):
    reject=(expected & INF)==INF
    w=root/version/name;w.mkdir(parents=True)
    source=f"value({token}).\nmain :- value(_), write('OK'), nl, halt.\n:- initialization(main).\n"
    (w/"probe.pl").write_text(source)
    env=dict(os.environ,PATH=str(bindir)+os.pathsep+os.environ.get("PATH",""))
    record={"source_sha256":hashlib.sha256(source.encode()).hexdigest(),"modes":{}}
    for stage in ("compile","consulted"):
        output=w/(stage+".trace")
        e=dict(env,**{TRACE:str(output)})
        cmd=([bindir/"gplc","--no-top-level","-o","probe_native","probe.pl"]
             if stage=="compile" else
             [bindir/"gprolog","--quiet","--consult-file","probe.pl"])
        run=execute(cmd,w,e)
        record["modes"][stage]={"command":run,"traces":parse_trace(output)}
        check_one(stage,record["modes"][stage],token,expected,reject,
                  name+"/"+version+"/"+stage,errors)
        if stage=="compile" and not reject and run["code"]==0:
            native=execute([w/"probe_native"],w,env)
            record["modes"]["native"]=native
            if native["code"]!=0 or native["output"].strip()!="OK":
                errors.append(name+"/"+version+": native known-answer output wrong")
    return record

def verify(baseline,candidate,out):
    selftest()
    for name,bindir in [("baseline",baseline),("candidate",candidate)]:
        for binary in ("gplc","gprolog","pl2wam"):
            if not (bindir/binary).is_file(): raise RuntimeError("Missing "+name+"/"+binary)
    result={"claim":"Exact decimal finite conversion agrees with integer-rational nearest-even oracle",
       "baseline":"pre-guard historical SHA 46a32b7c (finite cases only)",
       "candidate":"post-guard experimental GNU Prolog fork",
       "scope":"Linux ELF64/i686, independently generated deterministic cases",
       "seed":SEED,"cases":[],"errors":[],"passed":False}
    out.parent.mkdir(parents=True,exist_ok=True)
    def save():out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    with tempfile.TemporaryDirectory(prefix="gprolog-exact-decimal-") as temp:
        work=Path(temp)
        for name,token,want in cases():
            reject=(want&INF)==INF
            entry={"name":name,"literal":token,"token_length":len(token),
                   "expected_bits":f"{want:016x}",
                   "oracle":"reject" if reject else "accept","versions":{}}
            result["cases"].append(entry)
            for version,bindir in [("baseline",baseline),("candidate",candidate)]:
                if version=="baseline" and reject:
                    entry["versions"][version]={"skipped":"historical overflow crash already recorded in CI 44031708229"}
                    continue
                entry["versions"][version]=run_case(name,token,want,version,bindir,work,result["errors"])
            if not reject:
                for mode in ("compile","consulted"):
                    before=entry["versions"]["baseline"]["modes"][mode]["traces"]
                    after=entry["versions"]["candidate"]["modes"][mode]["traces"]
                    if before!=after:
                        result["errors"].append(name+"/"+mode+": baseline/candidate trace differs")
            save()
            print(f"{name:28s} {'REJECT' if reject else 'FINITE':6s} {want:016x} "
                  f"len={len(token):3d} cumulative_errors={len(result['errors'])}",flush=True)
    result["passed"]=not result["errors"];save()
    for message in result["errors"][:70]:print("FAIL:",message,flush=True)
    print(f"TOTAL={len(result['cases'])}, ERRORS={len(result['errors'])}, JSON={out}",flush=True)
    if result["errors"]:raise SystemExit(1)
    print("PASS finite IEEE754 bit equality, matched historical controls, controlled overflow rejection")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="task",required=True)
    a=sub.add_parser("instrument")
    a.add_argument("--lexer",type=Path,required=True)
    a.add_argument("--parser",type=Path,required=True)
    sub.add_parser("selftest")
    b=sub.add_parser("verify")
    b.add_argument("--baseline-bin",type=Path,required=True)
    b.add_argument("--candidate-bin",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    arg=parser.parse_args()
    if arg.task=="instrument":instrument(arg.lexer,arg.parser)
    elif arg.task=="selftest":selftest()
    else:verify(arg.baseline_bin.resolve(),arg.candidate_bin.resolve(),arg.output.resolve())

if __name__=="__main__":main()
