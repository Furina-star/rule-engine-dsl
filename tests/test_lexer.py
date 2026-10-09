import unittest

from errors import LexerError
from lexer import Lexer, TokenType as T


class LexerTests(unittest.TestCase):
    def test_all_keywords(self):
        tokens = Lexer("let rule when if else while print true false").tokenize()
        self.assertEqual([token.type for token in tokens],
                         [T.LET, T.RULE, T.WHEN, T.IF, T.ELSE, T.WHILE,
                          T.PRINT, T.TRUE, T.FALSE, T.EOF])

    def test_identifiers_and_keyword_boundaries(self):
        tokens = Lexer("letter rule2 _private Score TRUE").tokenize()
        self.assertEqual([token.lexeme for token in tokens[:-1]],
                         ["letter", "rule2", "_private", "Score", "TRUE"])
        self.assertTrue(all(token.type == T.IDENTIFIER for token in tokens[:-1]))

    def test_numbers_and_strings(self):
        tokens = Lexer('0 123 12.50 "hello world" ""').tokenize()
        self.assertEqual([token.literal for token in tokens[:-1]],
                         [0, 123, 12.5, "hello world", ""])
        self.assertIs(type(tokens[0].literal), int)
        self.assertIs(type(tokens[2].literal), float)

    def test_string_escapes(self):
        token = Lexer(r'"line\n\t\"quote\"\\\r"').tokenize()[0]
        self.assertEqual(token.literal, 'line\n\t"quote"\\\r')

    def test_all_operators_and_delimiters(self):
        tokens = Lexer("+ - * / = == != > >= < <= && || ! ( ) { } ;").tokenize()
        self.assertEqual([token.type for token in tokens],
                         [T.PLUS, T.MINUS, T.STAR, T.SLASH, T.EQUAL, T.EQUAL_EQUAL,
                          T.BANG_EQUAL, T.GREATER, T.GREATER_EQUAL, T.LESS,
                          T.LESS_EQUAL, T.AND, T.OR, T.BANG, T.LEFT_PAREN,
                          T.RIGHT_PAREN, T.LEFT_BRACE, T.RIGHT_BRACE, T.SEMICOLON, T.EOF])

    def test_adjacent_tokens_preserve_lexemes_literals_and_positions(self):
        tokens = Lexer("a1==12.5!=2;").tokenize()
        self.assertEqual(
            [(token.type, token.lexeme, token.literal, token.line, token.column)
             for token in tokens],
            [(T.IDENTIFIER, "a1", None, 1, 1),
             (T.EQUAL_EQUAL, "==", None, 1, 3),
             (T.NUMBER, "12.5", 12.5, 1, 5),
             (T.BANG_EQUAL, "!=", None, 1, 9),
             (T.NUMBER, "2", 2, 1, 11),
             (T.SEMICOLON, ";", None, 1, 12),
             (T.EOF, "", None, 1, 13)],
        )

    def test_comments_whitespace_and_division(self):
        tokens = Lexer(' \t// comment\n 8 / 2; // end').tokenize()
        self.assertEqual([token.type for token in tokens],
                         [T.NUMBER, T.SLASH, T.NUMBER, T.SEMICOLON, T.EOF])
        self.assertEqual((tokens[0].line, tokens[0].column), (2, 2))

    def test_comment_markers_inside_string(self):
        self.assertEqual(Lexer('"https://example"').tokenize()[0].literal, "https://example")

    def test_newline_formats_and_eof_location(self):
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                tokens = Lexer("let x = 1;" + newline + "  print(x);").tokenize()
                self.assertEqual((tokens[5].line, tokens[5].column), (2, 3))
                self.assertEqual((tokens[-1].line, tokens[-1].column), (2, 12))

    def test_empty_source(self):
        tokens = Lexer("").tokenize()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].type, T.EOF)
        self.assertEqual((tokens[0].line, tokens[0].column), (1, 1))

    def test_invalid_characters(self):
        for character in ("@", "&", "|", "'", "%", "[", "²"):
            with self.subTest(character=character):
                with self.assertRaisesRegex(LexerError, "line 2, column 3.*Unsupported character"):
                    Lexer("\n  " + character).tokenize()

    def test_unterminated_strings(self):
        for source in ('"hello', '"hello\nworld"', '"hello' + "\\"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(LexerError, "Unterminated string"):
                    Lexer(source).tokenize()

    def test_unknown_escape(self):
        with self.assertRaisesRegex(LexerError, "Unsupported string escape"):
            Lexer(r'"bad\q"').tokenize()

    def test_malformed_and_nonfinite_numbers(self):
        for source in ("1.", "1.2.3", ".5", "9" * 400 + ".0"):
            with self.subTest(source=source[:30]):
                with self.assertRaises(LexerError):
                    Lexer(source).tokenize()

    def test_incomplete_decimal_reports_number_start(self):
        for suffix in ("", " ", "\n", ";"):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(
                    LexerError, "Expected a digit after decimal point"
                ) as caught:
                    Lexer("\n  12." + suffix).tokenize()
                self.assertEqual((caught.exception.line, caught.exception.column), (2, 3))


if __name__ == "__main__":
    unittest.main()
