"""
CPSC 323 - Assignment 3: Symbol Table & Code Generation for Rat26S
Extends the Recursive Descent Parser (Assignment 2) with:
  1) Symbol table management
  2) Assembly code generation for simplified Rat26S

Simplified Rat26S: NO Function Definitions
Only provided instructions I1-I18 are used. No custom instructions created.

Semantics enforced:
  - true = 1, false = 0
  - No arithmetic operations allowed on booleans
  - Types must match for arithmetic operations (no implicit conversions)
  - Type must match on assignment
"""

import sys
from lexer import Lexer


class Parser:

    def __init__(self, source, output, switch=False):
        self.lex    = Lexer(source)
        self.tok    = None
        self.output = output
        self.switch = switch     # True -> also print grammar production rules
        self.next()

        # ── Symbol Table ──────────────────────────────────────────────────────
        self.symbol_table   = {}   # lexeme -> {'address': int, 'type': str}
        self.memory_address = 10000

        # ── Instruction Table ─────────────────────────────────────────────────
        # Python list grows dynamically; semantically holds >= 1000 instructions
        self.instr_table   = []    # each entry: [addr, op, operand_or_None]
        self.instr_address = 1     # next instruction slot (1-indexed)

        # ── Jump Stack for back-patching ──────────────────────────────────────
        self.jump_stack = []

    # ─────────────────────────────────────────────────────────────────────────
    # CORE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def next(self):
        self.tok = self.lex.lexer()

    def write(self, text):
        print(text)
        self.output.write(text + "\n")

    def rule(self, r):
        if self.switch:
            self.write(f"    {r}")

    def token(self):
        if self.switch and self.tok:
            self.write(f"Token : {self.tok.token_type:<15} Lexeme: {self.tok.lexeme}")

    def error(self, expected):
        lex = self.tok.lexeme     if self.tok else "EOF"
        typ = self.tok.token_type if self.tok else "EOF"
        self.write(
            f"SYNTAX ERROR: Expected {expected} "
            f"but received token = '{typ}' lexeme = '{lex}'"
        )
        sys.exit(1)

    def semantic_error(self, msg):
        self.write(f"SEMANTIC ERROR: {msg}")
        sys.exit(1)

    def match(self, value):
        if self.tok and self.tok.lexeme == value:
            self.token()
            self.next()
        else:
            self.error(f"'{value}'")

    def match_type(self, ttype):
        if self.tok and self.tok.token_type == ttype:
            self.token()
            self.next()
        else:
            self.error(ttype)

    def lexer_is(self, *values):
        return self.tok and self.tok.lexeme in values

    def type_is(self, ttype):
        return self.tok and self.tok.token_type == ttype

    # ─────────────────────────────────────────────────────────────────────────
    # SYMBOL TABLE  (Part 1)
    # ─────────────────────────────────────────────────────────────────────────

    def insert_symbol(self, lexeme, dtype):
        """Insert identifier; semantic error on duplicate declaration."""
        if lexeme in self.symbol_table:
            self.semantic_error(f"'{lexeme}' is already declared.")
        self.symbol_table[lexeme] = {
            'address': self.memory_address,
            'type':    dtype,
        }
        self.memory_address += 1

    def get_address(self, lexeme):
        """Return memory address; semantic error if not declared."""
        if lexeme not in self.symbol_table:
            self.semantic_error(f"'{lexeme}' was used without being declared.")
        return self.symbol_table[lexeme]['address']

    def get_type(self, lexeme):
        """Return declared type; semantic error if not declared."""
        if lexeme not in self.symbol_table:
            self.semantic_error(f"'{lexeme}' was used without being declared.")
        return self.symbol_table[lexeme]['type']

    def print_symbol_table(self):
        self.write("\nSymbol Table")
        self.write(f"{'Identifier':<20} {'MemoryLocation':<20} {'Type'}")
        for lexeme, info in self.symbol_table.items():
            self.write(f"{lexeme:<20} {info['address']:<20} {info['type']}")

    # ─────────────────────────────────────────────────────────────────────────
    # CODE GENERATION  (Part 2)
    # Only instructions I1–I18 are used. No custom instructions created.
    # ─────────────────────────────────────────────────────────────────────────

    def gen(self, op, operand=None):
        """Append instruction and advance counter (list holds >= 1000 entries)."""
        self.instr_table.append([self.instr_address, op, operand])
        self.instr_address += 1

    def push_jump_stack(self, addr):
        self.jump_stack.append(addr)

    def pop_jump_stack(self):
        if not self.jump_stack:
            self.write("INTERNAL ERROR: Jump stack underflow.")
            sys.exit(1)
        return self.jump_stack.pop()

    def back_patch(self, target):
        """Pop jump stack; fill that instruction's operand with target."""
        addr = self.pop_jump_stack()
        self.instr_table[addr - 1][2] = target

    def patch(self, instr_addr, target):
        """Directly patch a known instruction address."""
        self.instr_table[instr_addr - 1][2] = target

    def print_instructions(self):
        """Print instruction table; nil operands omitted per assignment spec."""
        for row in self.instr_table:
            addr, op, operand = row
            if operand is not None:
                self.write(f"{addr:<6} {op:<10} {operand}")
            else:
                self.write(f"{addr:<6} {op}")

    # ─────────────────────────────────────────────────────────────────────────
    # GRAMMAR  —  Simplified Rat26S  (NO Function Definitions)
    # ─────────────────────────────────────────────────────────────────────────

    def rat26s(self):
        """<Rat26S> -> @ <Opt Declaration List> <Statement List>"""
        self.rule("<Rat26S> -> @ <Opt Declaration List> <Statement List>")
        self.match("@")
        self.opt_decl_list()
        self.statement_list()

    # ── Declarations ─────────────────────────────────────────────────────────

    def qualifier(self):
        """Parse type keyword; return it as a string."""
        self.rule("<Qualifier> -> integer | boolean | real")
        if self.lexer_is("integer", "boolean", "real"):
            dtype = self.tok.lexeme
            self.token()
            self.next()
            return dtype
        else:
            self.error("qualifier (integer, boolean, real)")

    def opt_decl_list(self):
        self.rule("<Opt Declaration List> -> <Declaration List> | e")
        if self.lexer_is("integer", "boolean", "real"):
            self.decl_list()

    def decl_list(self):
        self.rule("<Declaration List> -> <Declaration> ; <Declaration List'>")
        while self.lexer_is("integer", "boolean", "real"):
            self.declaration()
            self.match(";")

    def declaration(self):
        """Parse declaration; insert each identifier into the symbol table."""
        self.rule("<Declaration> -> <Qualifier> <IDs>")
        dtype = self.qualifier()
        self.ids(dtype)

    def ids(self, dtype=None):
        """Parse comma-separated identifiers; insert into symbol table if dtype given."""
        self.rule("<IDs> -> <Identifier> <IDs'>")
        lexeme = self.tok.lexeme if self.tok else None
        self.match_type("identifier")
        if dtype is not None:
            self.insert_symbol(lexeme, dtype)
        while self.lexer_is(","):
            self.match(",")
            lexeme = self.tok.lexeme if self.tok else None
            self.match_type("identifier")
            if dtype is not None:
                self.insert_symbol(lexeme, dtype)

    # ── Statements ────────────────────────────────────────────────────────────

    def statement_list(self):
        self.rule("<Statement List> -> <Statement> <Statement List'>")
        lexer_starters = {"{", "if", "return", "write", "read", "while"}
        while self.lexer_is(*lexer_starters) or self.type_is("identifier"):
            self.statement()

    def statement(self):
        self.rule(
            "<Statement> -> <Compound> | <Assign> | <If> | "
            "<Return> | <Print> | <Scan> | <While>"
        )
        if   self.lexer_is("{"):          self.compound()
        elif self.lexer_is("if"):         self.if_statement()
        elif self.lexer_is("return"):     self.return_statement()
        elif self.lexer_is("write"):      self.print_statement()
        elif self.lexer_is("read"):       self.scan()
        elif self.lexer_is("while"):      self.while_statement()
        elif self.type_is("identifier"):  self.assign()
        else:                             self.error("statement")

    def compound(self):
        self.rule("<Compound> -> { <Statement List> }")
        self.match("{")
        self.statement_list()
        self.match("}")

    def assign(self):
        """
        <Assign> -> id = <Expression> ;
        Semantic actions:
          - Verify id is declared
          - Evaluate expression (returns its type)
          - Check that RHS type matches LHS type
          - Generate POPM addr(id)   [I3]
        """
        self.rule("<Assign> -> <Identifier> = <Expression> ;")
        lexeme = self.tok.lexeme if self.tok else None
        self.match_type("identifier")
        lhs_type = self.get_type(lexeme)      # also verifies id is declared
        lhs_addr = self.get_address(lexeme)
        self.match("=")
        rhs_type = self.expression()          # leaves result on stack; returns type
        self.match(";")

        # Type match check (requirement: types must match)
        if lhs_type != rhs_type:
            self.semantic_error(
                f"Type mismatch in assignment to '{lexeme}': "
                f"variable is '{lhs_type}' but expression is '{rhs_type}'."
            )

        self.gen("POPM", lhs_addr)            # I3

    def if_statement(self):
        """
        <If> -> if ( <Condition> ) <Statement> fi
              | if ( <Condition> ) <Statement> otherwise <Statement> fi

        Without otherwise:
            <condition> -> JMPZ ?
            <body>
            back_patch -> LABEL

        With otherwise:
            <condition> -> JMPZ ?
            <then body>
            JMP ?
            LABEL        <- JMPZ patched here (start of else)
            <else body>
            LABEL        <- JMP patched here  (end of if)
        """
        self.rule("<If> -> if ( <Condition> ) <Statement> <If'>")
        self.match("if")
        self.match("(")
        self.condition()            # generates comparison + JMPZ (addr on jump_stack)
        self.match(")")
        self.statement()

        if self.lexer_is("otherwise"):
            self.rule("<If'> -> otherwise <Statement> fi")
            self.match("otherwise")
            jmp_addr = self.instr_address
            self.gen("JMP")                             # I17: skip else; patch later
            self.back_patch(self.instr_address)         # JMPZ -> start of else
            self.gen("LABEL")                           # I18: start of else
            self.statement()
            self.match("fi")
            self.patch(jmp_addr, self.instr_address)    # JMP -> end of if
            self.gen("LABEL")                           # I18: end of if
        else:
            self.rule("<If'> -> fi")
            self.match("fi")
            self.back_patch(self.instr_address)         # JMPZ -> end of if
            self.gen("LABEL")                           # I18: end of if

    def return_statement(self):
        self.rule("<Return> -> return <Return'>")
        self.match("return")
        if self.lexer_is(";"):
            self.rule("<Return'> -> ;")
            self.match(";")
        else:
            self.rule("<Return'> -> <Expression> ;")
            self.expression()
            self.match(";")

    def print_statement(self):
        """<Print> -> write ( <Expression> ) ;   Semantic: SOUT [I4]"""
        self.rule("<Print> -> write ( <Expression> ) ;")
        self.match("write")
        self.match("(")
        self.expression()           # leaves value on stack
        self.match(")")
        self.match(";")
        self.gen("SOUT")            # I4

    def scan(self):
        """<Scan> -> read ( <IDs> ) ;   Semantic: SIN [I5] + POPM [I3] per identifier"""
        self.rule("<Scan> -> read ( <IDs> ) ;")
        self.match("read")
        self.match("(")
        lexeme = self.tok.lexeme if self.tok else None
        self.match_type("identifier")
        self.gen("SIN")                              # I5
        self.gen("POPM", self.get_address(lexeme))   # I3
        while self.lexer_is(","):
            self.match(",")
            lexeme = self.tok.lexeme if self.tok else None
            self.match_type("identifier")
            self.gen("SIN")
            self.gen("POPM", self.get_address(lexeme))
        self.match(")")
        self.match(";")

    def while_statement(self):
        """
        <While> -> while ( <Condition> ) <Statement>

        LABEL  <- Ar (loop top)          [I18]
        <condition>  -> JMPZ ? (jump_stack)
        <body>
        JMP Ar                           [I17]
        (JMPZ patched to instruction after JMP: loop exit)
        """
        self.rule("<While> -> while ( <Condition> ) <Statement>")
        Ar = self.instr_address
        self.gen("LABEL")           # I18: loop top
        self.match("while")
        self.match("(")
        self.condition()            # generates comparison + JMPZ (addr on jump_stack)
        self.match(")")
        self.statement()
        self.gen("JMP", Ar)         # I17: back to LABEL
        self.back_patch(self.instr_address)  # JMPZ -> instruction after JMP (exit)

    def condition(self):
        """
        <Condition> -> <Expression> <Relop> <Expression>
        Generates: comparison instruction (I10-I15), then JMPZ [I16] pushed to jump_stack.
        """
        self.rule("<Condition> -> <Expression> <Relop> <Expression>")
        self.expression()
        op = self.tok.lexeme if self.tok else None
        self.relop()
        self.expression()

        # Map relop to provided instructions I10-I15 only
        op_map = {
            "==": "EQU",   # I12
            "!=": "NEQ",   # I13
            ">":  "GRT",   # I10
            "<":  "LES",   # I11
            ">=": "GEQ",   # I14
            "=>": "GEQ",   # alternate lexer spelling for >=
            "<=": "LEQ",   # I15
        }
        instr = op_map.get(op)
        if not instr:
            self.write(f"INTERNAL ERROR: Unknown relop '{op}'")
            sys.exit(1)
        self.gen(instr)

        # I16: JMPZ nil — address saved on jump_stack for back-patching
        self.push_jump_stack(self.instr_address)
        self.gen("JMPZ")

    def relop(self):
        self.rule("<Relop> -> == | != | > | < | <= | >=")
        if self.lexer_is("==", "!=", ">", "<", "<=", ">=", "=>"):
            self.token()
            self.next()
        else:
            self.error("relational operator (==, !=, >, <, <=, >=)")

    # ── Expressions  (each returns its type as a string) ─────────────────────

    def expression(self):
        """
        <Expression> -> <Term> <Expression'>
        <Expression'> -> + <Term> { gen A [I6] } <Expression'>
                       | - <Term> { gen S [I7] } <Expression'>
                       | e
        Returns: type of the expression (used for type checking).
        Semantic: boolean operands are not allowed in arithmetic.
        """
        self.rule("<Expression> -> <Term> <Expression'>")
        expr_type = self.term()

        while self.lexer_is("+", "-"):
            op = self.tok.lexeme
            if op == "+":
                self.rule("<Expression'> -> + <Term> <Expression'>")
            else:
                self.rule("<Expression'> -> - <Term> <Expression'>")
            self.token()
            self.next()
            rhs_type = self.term()

            # Requirement: no arithmetic on booleans; types must match
            if expr_type == "boolean":
                self.semantic_error(
                    f"Arithmetic operator '{op}' cannot be applied to boolean."
                )
            if rhs_type == "boolean":
                self.semantic_error(
                    f"Arithmetic operator '{op}' cannot be applied to boolean."
                )
            if expr_type != rhs_type:
                self.semantic_error(
                    f"Type mismatch: cannot apply '{op}' to '{expr_type}' and '{rhs_type}'."
                )

            self.gen("A" if op == "+" else "S")   # I6 or I7
            # type stays the same after arithmetic

        self.rule("<Expression'> -> e")
        return expr_type

    def term(self):
        """
        <Term> -> <Factor> <Term'>
        <Term'> -> * <Factor> { gen M [I8] } <Term'>
                 | / <Factor> { gen D [I9] } <Term'>
                 | e
        Returns: type of the term.
        Semantic: boolean operands are not allowed in arithmetic.
        """
        self.rule("<Term> -> <Factor> <Term'>")
        term_type = self.factor()

        while self.lexer_is("*", "/"):
            op = self.tok.lexeme
            if op == "*":
                self.rule("<Term'> -> * <Factor> <Term'>")
            else:
                self.rule("<Term'> -> / <Factor> <Term'>")
            self.token()
            self.next()
            rhs_type = self.factor()

            # Requirement: no arithmetic on booleans; types must match
            if term_type == "boolean":
                self.semantic_error(
                    f"Arithmetic operator '{op}' cannot be applied to boolean."
                )
            if rhs_type == "boolean":
                self.semantic_error(
                    f"Arithmetic operator '{op}' cannot be applied to boolean."
                )
            if term_type != rhs_type:
                self.semantic_error(
                    f"Type mismatch: cannot apply '{op}' to '{term_type}' and '{rhs_type}'."
                )

            self.gen("M" if op == "*" else "D")   # I8 or I9

        self.rule("<Term'> -> e")
        return term_type

    def factor(self):
        """
        <Factor> -> - <Primary>   unary negation: PUSHI 0 [I1], primary, S [I7]
                  | <Primary>
        Returns: type of the factor.
        Semantic: cannot negate a boolean.
        """
        if self.lexer_is("-"):
            self.rule("<Factor> -> - <Primary>")
            self.match("-")
            self.gen("PUSHI", 0)        # I1: push 0
            ptype = self.primary()
            if ptype == "boolean":
                self.semantic_error("Unary negation cannot be applied to boolean.")
            self.gen("S")               # I7: 0 - value = -value
            return ptype
        else:
            self.rule("<Factor> -> <Primary>")
            return self.primary()

    def primary(self):
        """
        <Primary> -> id           -> PUSHM addr  [I2]   ; returns declared type
                   | id ( args )  -> function call (grammar only; simplified has no functions)
                   | integer      -> PUSHI val   [I1]   ; returns 'integer'
                   | real         -> PUSHI val   [I1]   ; returns 'real'
                   | ( Expression )              ; returns inner type
                   | true         -> PUSHI 1     [I1]   ; returns 'boolean'
                   | false        -> PUSHI 0     [I1]   ; returns 'boolean'
        """
        self.rule(
            "<Primary> -> <Identifier> | <Identifier> ( <Opt Arg List> ) "
            "| <Integer> | <Real> | ( <Expression> ) | true | false"
        )

        if self.type_is("identifier"):
            lexeme = self.tok.lexeme
            self.match_type("identifier")
            ptype = self.get_type(lexeme)   # also verifies declared
            if self.lexer_is("("):
                # Function call — parse arguments (grammar only; no code gen)
                self.match("(")
                self.opt_arg_list()
                self.match(")")
            else:
                self.gen("PUSHM", self.get_address(lexeme))   # I2
            return ptype

        elif self.type_is("integer"):
            val = self.tok.lexeme
            self.match_type("integer")
            self.gen("PUSHI", val)   # I1
            return "integer"

        elif self.type_is("real"):
            val = self.tok.lexeme
            self.match_type("real")
            self.gen("PUSHI", val)   # I1
            return "real"

        elif self.lexer_is("("):
            self.match("(")
            ptype = self.expression()
            self.match(")")
            return ptype

        elif self.lexer_is("true"):
            self.token()
            self.next()
            self.gen("PUSHI", 1)     # I1: true = 1
            return "boolean"

        elif self.lexer_is("false"):
            self.token()
            self.next()
            self.gen("PUSHI", 0)     # I1: false = 0
            return "boolean"

        else:
            self.error("primary (identifier, integer, real, '(', true, false)")


        self.rule("<Opt Argument List> -> <Argument List> | e")
        if not self.lexer_is(")"):
            self.arg_list()

    def arg_list(self):
        self.rule("<Argument List> -> <Expression> <Argument List'>")
        self.expression()
        while self.lexer_is(","):
            self.match(",")
            self.expression()


# ─────────────────────────────────────────────────────────────────────────────
# DRIVER
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(input_path, output_path, switch=False):
    """
    switch=False (default) -> assembly + symbol table only  [Assignment 3 mode]
    switch=True            -> also print grammar rules      [Assignment 2 style]
    """
    with open(input_path, 'r') as f:
        source = f.read()

    with open(output_path, 'w', encoding='utf-8') as out:
        p = Parser(source, out, switch)
        p.rat26s()

        if p.tok is not None:
            p.write(
                f"SYNTAX ERROR: Unexpected token '{p.tok.lexeme}' "
                "after end of program."
            )
        else:
            p.print_instructions()
            p.print_symbol_table()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parser.py <input_file> <output_file> [--rules]")
        sys.exit(1)
    show_rules = "--rules" in sys.argv
    parse_file(sys.argv[1], sys.argv[2], show_rules)