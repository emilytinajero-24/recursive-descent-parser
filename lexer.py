"""
CPSC 323 - Assignment 1: Lexical Analyzer (Lexer) for Rat26S
Spring 2026

FSM-based lexer implementing:
  - DFSM for Identifiers
  - DFSM for Integers
  - DFSM for Reals
  - Ad-hoc recognition for operators, separators, keywords, and comments
"""

import sys
import os

#  KEYWORDS (reserved words in Rat26S)
KEYWORDS = {
    "integer", "boolean", "real", "if", "otherwise", "fi",
    "while", "return", "read", "write", "true", "false", "function"
}

#  OPERATORS and SEPARATORS
OPERATORS = {"=", "+", "-", "*", "/", "==", "!=", "<", ">", "<=", "=>"}
SEPARATORS = {"(", ")", "{", "}", ",", ";", "@"}

#  TOKEN RECORD
class Token:
    def __init__(self, token_type: str, lexeme: str):
        self.token_type = token_type
        self.lexeme = lexeme

    def __repr__(self):
        return f"Token({self.token_type!r}, {self.lexeme!r})"


# ─────────────────────────────────────────────
#  FSM: IDENTIFIER
#
#  RE:  letter ( letter | digit | '_' )*
#
#  NFSM (Thompson construction):
#    State 0 --[letter]--> State 1 (accept)
#    State 1 --[letter|digit|_]--> State 1 (self-loop)
#
#  DFSM (after subset construction – same shape here since no ε-moves needed):
#    States: {START=0, IN_ID=1, DEAD=2}
#    Transitions:
#      (START, letter)        -> IN_ID
#      (IN_ID, letter|digit|_)-> IN_ID
#      (anything else)        -> DEAD
#    Accept: {IN_ID}
# ─────────────────────────────────────────────
class IdentifierFSM:
    START  = 0
    IN_ID  = 1
    DEAD   = 2

    ACCEPT = {IN_ID}

    def transition(self, state: int, ch: str) -> int:
        if state == self.START:
            if ch.isalpha():
                return self.IN_ID
        elif state == self.IN_ID:
            if ch.isalpha() or ch.isdigit() or ch == '_':
                return self.IN_ID
        return self.DEAD

    def run(self, source: str, pos: int):
        state = self.START
        lexeme = []
        i = pos
        while i < len(source):
            ch = source[i]
            next_state = self.transition(state, ch)
            if next_state == self.DEAD:
                break
            state = next_state
            lexeme.append(ch)
            i += 1
        if state in self.ACCEPT:
            return ''.join(lexeme), i
        return None, pos


# ─────────────────────────────────────────────
#  FSM: INTEGER
#
#  RE:  digit+
#
#  NFSM (Thompson):
#    State 0 --[digit]--> State 1 (accept)
#    State 1 --[digit]--> State 1 (self-loop)
#
#  DFSM:
#    States: {START=0, IN_INT=1, DEAD=2}
#    Transitions:
#      (START,  digit) -> IN_INT
#      (IN_INT, digit) -> IN_INT
#      (anything else) -> DEAD
#    Accept: {IN_INT}
# ─────────────────────────────────────────────
class IntegerFSM:
    START  = 0
    IN_INT = 1
    DEAD   = 2

    ACCEPT = {IN_INT}

    def transition(self, state: int, ch: str) -> int:
        if state in (self.START, self.IN_INT):
            if ch.isdigit():
                return self.IN_INT
        return self.DEAD

    def run(self, source: str, pos: int):
        state = self.START
        lexeme = []
        i = pos
        while i < len(source):
            ch = source[i]
            next_state = self.transition(state, ch)
            if next_state == self.DEAD:
                break
            state = next_state
            lexeme.append(ch)
            i += 1
        if state in self.ACCEPT:
            return ''.join(lexeme), i
        return None, pos


# ─────────────────────────────────────────────
#  FSM: REAL
#
#  RE:  digit+ '.' digit+
#
#  NFSM (Thompson):
#    0 --[digit]--> 1 --[digit]--> 1  (integer part, self-loop)
#    1 --['.'  ]--> 2
#    2 --[digit]--> 3 (accept)
#    3 --[digit]--> 3 (self-loop)
#
#  DFSM (identical structure after ε-closure – no ε-moves in this RE):
#    States: {START=0, INT_PART=1, DOT=2, FRAC_PART=3, DEAD=4}
#    Transitions:
#      (START,     digit) -> INT_PART
#      (INT_PART,  digit) -> INT_PART
#      (INT_PART,  '.')   -> DOT
#      (DOT,       digit) -> FRAC_PART
#      (FRAC_PART, digit) -> FRAC_PART
#      (anything else)    -> DEAD
#    Accept: {FRAC_PART}
# ─────────────────────────────────────────────
class RealFSM:
    START     = 0
    INT_PART  = 1
    DOT       = 2
    FRAC_PART = 3
    DEAD      = 4

    ACCEPT = {FRAC_PART}

    def transition(self, state: int, ch: str) -> int:
        if state == self.START:
            if ch.isdigit():
                return self.INT_PART
        elif state == self.INT_PART:
            if ch.isdigit():
                return self.INT_PART
            if ch == '.':
                return self.DOT
        elif state == self.DOT:
            if ch.isdigit():
                return self.FRAC_PART
        elif state == self.FRAC_PART:
            if ch.isdigit():
                return self.FRAC_PART
        return self.DEAD

    def run(self, source: str, pos: int):
        state = self.START
        lexeme = []
        i = pos
        while i < len(source):
            ch = source[i]
            next_state = self.transition(state, ch)
            if next_state == self.DEAD:
                break
            state = next_state
            lexeme.append(ch)
            i += 1
        if state in self.ACCEPT:
            return ''.join(lexeme), i
        return None, pos


# ─────────────────────────────────────────────
#  MAIN LEXER
# ─────────────────────────────────────────────
class Lexer:
    def __init__(self, source: str):
        self.source = source.lower()
        self.pos = 0
        self.id_fsm   = IdentifierFSM()
        self.int_fsm  = IntegerFSM()
        self.real_fsm = RealFSM()

    def _skip_whitespace_and_comments(self):
        """Skip blanks, tabs, newlines and /* ... */ comments."""
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch in (' ', '\t', '\n', '\r'):
                self.pos += 1
            elif self.source[self.pos:self.pos+2] == '/*':
                end = self.source.find('*/', self.pos + 2)
                if end == -1:
                    raise SyntaxError("Unterminated comment")
                self.pos = end + 2
            else:
                break

    def lexer(self):
        self._skip_whitespace_and_comments()
        if self.pos >= len(self.source):
            return None  # EOF

        lexeme, new_pos = self.real_fsm.run(self.source, self.pos)
        if lexeme is not None:
            self.pos = new_pos
            return Token("real", lexeme)

        lexeme, new_pos = self.int_fsm.run(self.source, self.pos)
        if lexeme is not None:
            self.pos = new_pos
            return Token("integer", lexeme)

        lexeme, new_pos = self.id_fsm.run(self.source, self.pos)
        if lexeme is not None:
            self.pos = new_pos
            token_type = "keyword" if lexeme in KEYWORDS else "identifier"
            return Token(token_type, lexeme)

        two_ch = self.source[self.pos:self.pos+2]
        if two_ch in OPERATORS:
            self.pos += 2
            return Token("operator", two_ch)

        one_ch = self.source[self.pos]
        if one_ch in OPERATORS:
            self.pos += 1
            return Token("operator", one_ch)

        if one_ch in SEPARATORS:
            self.pos += 1
            return Token("separator", one_ch)

        self.pos += 1
        return Token("unknown", one_ch)


# ─────────────────────────────────────────────
#  DRIVER (main program)
# ─────────────────────────────────────────────
def tokenize_file(input_path: str, output_path: str):
    with open(input_path, 'r') as f:
        source = f.read()

    lex = Lexer(source)
    tokens = []
    while True:
        tok = lex.lexer()
        if tok is None:
            break
        tokens.append(tok)

    header = f"{'token':<15} {'lexeme'}"
    separator_line = "-" * 35
    lines = [header, separator_line]
    for tok in tokens:
        lines.append(f"{tok.token_type:<15} {tok.lexeme}")

    output = "\n".join(lines) + "\n"

    with open(output_path, 'w') as f:
        f.write(output)

    print(output, end="")
    return tokens


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python lexer.py <input_file> <output_file>")
        sys.exit(1)
    tokenize_file(sys.argv[1], sys.argv[2])