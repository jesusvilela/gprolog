// SPDX-License-Identifier: LGPL-3.0-or-later OR GPL-2.0-or-later
//! Direct Rust Prolog parser, intentionally a finite Horn-clause subset.
use std::collections::HashMap;
use std::fmt;

pub const MAX_SOURCE_BYTES: usize = 2_000_000;
const MAX_NESTING: usize = 128;

#[derive(Clone, Debug, PartialEq)]
pub enum Term {
    Var(usize),
    Atom(String),
    Integer(i64),
    Float(u64),
    Struct(String, Vec<Term>),
}

impl Term {
    pub fn functor(&self) -> Option<(&str, usize)> {
        match self {
            Self::Atom(name) => Some((name, 0)),
            Self::Struct(name, args) => Some((name, args.len())),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Clause {
    pub head: Term,
    pub body: Vec<Term>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Program {
    pub clauses: Vec<Clause>,
    pub next_var: usize,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Query {
    pub goals: Vec<Term>,
    pub variables: Vec<(String, usize)>,
    pub next_var: usize,
}

#[derive(Clone, Debug, PartialEq)]
pub struct SyntaxError {
    pub offset: usize,
    pub message: String,
}

impl SyntaxError {
    fn new(offset: usize, message: impl Into<String>) -> Self {
        Self { offset, message: message.into() }
    }
}

impl fmt::Display for SyntaxError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "syntax at byte {}: {}", self.offset, self.message)
    }
}
impl std::error::Error for SyntaxError {}

#[derive(Clone, Debug, PartialEq)]
enum Kind {
    Atom(String),
    Variable(String),
    Integer(i64),
    Float(u64),
    LParen,
    RParen,
    LBracket,
    RBracket,
    Comma,
    Dot,
    Bar,
    Rule,
    Query,
    Equal,
    NotUnifiable,
    End,
}

#[derive(Clone, Debug)]
struct Token {
    kind: Kind,
    pos: usize,
}

fn is_name_tail(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

fn tokenize(source: &str) -> Result<Vec<Token>, SyntaxError> {
    if source.len() > MAX_SOURCE_BYTES {
        return Err(SyntaxError::new(0, "input exceeds source-byte limit"));
    }
    let bytes = source.as_bytes();
    let mut at = 0;
    let mut output = Vec::new();
    while at < bytes.len() {
        let begin = at;
        let c = bytes[at];
        if c.is_ascii_whitespace() {
            at += 1;
            continue;
        }
        if c == b'%' {
            while at < bytes.len() && bytes[at] != b'\n' { at += 1; }
            continue;
        }
        let kind = match c {
            b'(' => { at += 1; Kind::LParen }
            b')' => { at += 1; Kind::RParen }
            b'[' => { at += 1; Kind::LBracket }
            b']' => { at += 1; Kind::RBracket }
            b',' => { at += 1; Kind::Comma }
            b'.' => { at += 1; Kind::Dot }
            b'|' => { at += 1; Kind::Bar }
            b'=' => { at += 1; Kind::Equal }
            b':' if bytes.get(at + 1) == Some(&b'-') => {
                at += 2;
                Kind::Rule
            }
            b'?' if bytes.get(at + 1) == Some(&b'-') => {
                at += 2;
                Kind::Query
            }
            b'\\' if bytes.get(at + 1) == Some(&b'=') => {
                at += 2;
                Kind::NotUnifiable
            }
            b'\'' => {
                at += 1;
                let mut atom = String::new();
                let mut closed = false;
                while at < bytes.len() {
                    if bytes[at] == b'\'' {
                        at += 1;
                        if bytes.get(at) == Some(&b'\'') {
                            at += 1;
                            atom.push('\'');
                        } else {
                            closed = true;
                            break;
                        }
                    } else if bytes[at].is_ascii() && bytes[at] != b'\n' {
                        atom.push(bytes[at] as char);
                        at += 1;
                    } else {
                        return Err(SyntaxError::new(at, "unsupported character in quoted atom"));
                    }
                }
                if !closed {
                    return Err(SyntaxError::new(begin, "unterminated quoted atom"));
                }
                Kind::Atom(atom)
            }
            b'a'..=b'z' => {
                at += 1;
                while at < bytes.len() && is_name_tail(bytes[at]) { at += 1; }
                Kind::Atom(source[begin..at].to_string())
            }
            b'A'..=b'Z' | b'_' => {
                at += 1;
                while at < bytes.len() && is_name_tail(bytes[at]) { at += 1; }
                Kind::Variable(source[begin..at].to_string())
            }
            b'0'..=b'9' | b'-' | b'+' if c.is_ascii_digit()
                || ((c == b'-' || c == b'+')
                    && bytes.get(at + 1).is_some_and(u8::is_ascii_digit)) =>
            {
                if c == b'+' || c == b'-' { at += 1; }
                while at < bytes.len() && bytes[at].is_ascii_digit() { at += 1; }
                let has_fraction =
                    bytes.get(at) == Some(&b'.') &&
                    bytes.get(at + 1).is_some_and(u8::is_ascii_digit);
                if has_fraction {
                    at += 1;
                    while at < bytes.len() && bytes[at].is_ascii_digit() { at += 1; }
                    if matches!(bytes.get(at), Some(b'e' | b'E')) {
                        at += 1;
                        if matches!(bytes.get(at), Some(b'+' | b'-')) { at += 1; }
                        let exponent_start = at;
                        while at < bytes.len() && bytes[at].is_ascii_digit() {
                            at += 1;
                        }
                        if exponent_start == at {
                            return Err(SyntaxError::new(at, "missing exponent digits"));
                        }
                    }
                    let raw = &source[begin..at];
                    let parsed = raw.parse::<f64>()
                        .map_err(|_| SyntaxError::new(begin, "invalid floating literal"))?;
                    if !parsed.is_finite() {
                        return Err(SyntaxError::new(begin, "non-finite floating literal"));
                    }
                    Kind::Float(parsed.to_bits())
                } else {
                    let raw = &source[begin..at];
                    let value = raw.parse::<i64>()
                        .map_err(|_| SyntaxError::new(begin, "integer outside i64 range"))?;
                    Kind::Integer(value)
                }
            }
            _ => {
                return Err(SyntaxError::new(begin,
                    format!("unsupported token byte 0x{c:02x}")));
            }
        };
        output.push(Token { kind, pos: begin });
    }
    output.push(Token { kind: Kind::End, pos: source.len() });
    Ok(output)
}

struct Parser {
    tokens: Vec<Token>,
    at: usize,
    next_var: usize,
    scope: HashMap<String, usize>,
    order: Vec<(String, usize)>,
}

impl Parser {
    fn new(text: &str, next_var: usize) -> Result<Self, SyntaxError> {
        Ok(Self { tokens: tokenize(text)?, at: 0, next_var,
            scope: HashMap::new(), order: Vec::new() })
    }

    fn current(&self) -> &Kind {
        &self.tokens[self.at].kind
    }

    fn offset(&self) -> usize {
        self.tokens[self.at].pos
    }

    fn advance(&mut self) -> Kind {
        let token = self.tokens[self.at].kind.clone();
        if self.at + 1 < self.tokens.len() { self.at += 1; }
        token
    }

    fn consume(&mut self, expected: &Kind) -> bool {
        if self.current() == expected { self.advance(); true } else { false }
    }

    fn expect(&mut self, expected: &Kind, label: &str) -> Result<(), SyntaxError> {
        if self.consume(expected) {
            Ok(())
        } else {
            Err(SyntaxError::new(self.offset(), format!("expected {label}")))
        }
    }

    fn new_var(&mut self, name: String) -> usize {
        if name != "_" {
            if let Some(var) = self.scope.get(&name) { return *var; }
        }
        let id = self.next_var;
        self.next_var += 1;
        if name != "_" {
            self.scope.insert(name.clone(), id);
            self.order.push((name, id));
        }
        id
    }

    fn term(&mut self, depth: usize) -> Result<Term, SyntaxError> {
        if depth > MAX_NESTING {
            return Err(SyntaxError::new(self.offset(), "term nesting limit exceeded"));
        }
        let pos = self.offset();
        match self.advance() {
            Kind::Variable(name) => Ok(Term::Var(self.new_var(name))),
            Kind::Integer(n) => Ok(Term::Integer(n)),
            Kind::Float(bits) => Ok(Term::Float(bits)),
            Kind::Atom(name) => {
                if !self.consume(&Kind::LParen) { return Ok(Term::Atom(name)); }
                let mut args = Vec::new();
                args.push(self.term(depth + 1)?);
                while self.consume(&Kind::Comma) {
                    args.push(self.term(depth + 1)?);
                }
                self.expect(&Kind::RParen, "')'")?;
                Ok(Term::Struct(name, args))
            }
            Kind::LParen => {
                let inner = self.term(depth + 1)?;
                self.expect(&Kind::RParen, "')'")?;
                Ok(inner)
            }
            Kind::LBracket => {
                if self.consume(&Kind::RBracket) {
                    return Ok(Term::Atom("[]".into()));
                }
                let mut values = vec![self.term(depth + 1)?];
                while self.consume(&Kind::Comma) {
                    values.push(self.term(depth + 1)?);
                }
                let mut tail = if self.consume(&Kind::Bar) {
                    self.term(depth + 1)?
                } else {
                    Term::Atom("[]".into())
                };
                self.expect(&Kind::RBracket, "']'")?;
                for value in values.into_iter().rev() {
                    tail = Term::Struct(".".into(), vec![value, tail]);
                }
                Ok(tail)
            }
            _ => Err(SyntaxError::new(pos, "expected a Prolog term")),
        }
    }

    fn goal(&mut self) -> Result<Term, SyntaxError> {
        let lhs = self.term(0)?;
        if self.consume(&Kind::Equal) {
            Ok(Term::Struct("=".into(), vec![lhs, self.term(0)?]))
        } else if self.consume(&Kind::NotUnifiable) {
            Ok(Term::Struct("\\=".into(), vec![lhs, self.term(0)?]))
        } else {
            Ok(lhs)
        }
    }

    fn goals(&mut self) -> Result<Vec<Term>, SyntaxError> {
        let mut values = vec![self.goal()?];
        while self.consume(&Kind::Comma) {
            values.push(self.goal()?);
        }
        Ok(values)
    }
}

pub fn parse_program(source: &str) -> Result<Program, SyntaxError> {
    let mut parser = Parser::new(source, 0)?;
    let mut clauses = Vec::new();
    while parser.current() != &Kind::End {
        parser.scope.clear();
        parser.order.clear();
        let head = parser.term(0)?;
        if head.functor().is_none() {
            return Err(SyntaxError::new(parser.offset(),
                "clause head must be a callable atom or structure"));
        }
        let body = if parser.consume(&Kind::Rule) {
            parser.goals()?
        } else { Vec::new() };
        parser.expect(&Kind::Dot, "'.' after clause")?;
        clauses.push(Clause { head, body });
    }
    Ok(Program { clauses, next_var: parser.next_var })
}

pub fn parse_query(source: &str, next_var: usize) -> Result<Query, SyntaxError> {
    let mut parser = Parser::new(source, next_var)?;
    parser.consume(&Kind::Query);
    let goals = parser.goals()?;
    parser.expect(&Kind::Dot, "'.' after query")?;
    parser.expect(&Kind::End, "end of query")?;
    Ok(Query {
        goals,
        variables: parser.order,
        next_var: parser.next_var,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_ancestor_and_vars() {
        let program = parse_program("parent(ada,noah). ancestor(X,Y):-parent(X,Y).").unwrap();
        assert_eq!(program.clauses.len(), 2);
        let query = parse_query("?- ancestor(ada, Who).", program.next_var).unwrap();
        assert_eq!(query.variables.len(), 1);
        assert_eq!(query.variables[0].0, "Who");
    }

    #[test]
    fn lists_and_quoted_atoms() {
        let program = parse_program("member(X,[X|_]). member(X,[_|T]):-member(X,T).").unwrap();
        assert_eq!(program.clauses.len(), 2);
        let query = parse_query("member(X,['two words',b]).", program.next_var).unwrap();
        assert_eq!(query.variables[0].0, "X");
    }

    #[test]
    fn invalid_input_and_nonfinite_are_errors() {
        assert!(parse_program("value(1.0e309).").is_err());
        assert!(parse_program("bad([a,b).").is_err());
        assert!(parse_program("p('unterminated).").is_err());
        assert!(parse_program("p(99999999999999999999999).").is_err());
        assert!(parse_query("p(a). q(b).", 0).is_err());
    }

    #[test]
    fn variable_scope_and_anonymous_vars() {
        let p = parse_program("p(_,X,_). p(X,X).").unwrap();
        let Term::Struct(_, ref args) = p.clauses[0].head else { panic!() };
        assert_ne!(args[0], args[1]);
        assert_ne!(args[0], args[2]);
        let Term::Struct(_, ref same) = p.clauses[1].head else { panic!() };
        assert_eq!(same[0], same[1]);
    }

    #[test]
    fn float_signed_zero_and_locale_independence() {
        let p = parse_program("p(-0.0). p(5.0e-324).").unwrap();
        let Term::Struct(_, ref a) = p.clauses[0].head else { panic!() };
        assert_eq!(a[0], Term::Float(0x8000_0000_0000_0000));
        let Term::Struct(_, ref b) = p.clauses[1].head else { panic!() };
        assert_eq!(b[0], Term::Float(1));
    }
}
