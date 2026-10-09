"""Test tokenization, source positions, string escapes, and lexical errors."""

import unittest

from errors import LexerError
from lexer import Lexer, TokenType


class LexerTests(unittest.TestCase):
    def test_all_keywords(self):
        tokens = Lexer("let rule when if else while print true false").tokenize()
        self.assertEqual([TokenType.LET, TokenType.RULE, TokenType.WHEN, TokenType.IF, TokenType.ELSE, TokenType.WHILE,
                          TokenType.PRINT, TokenType.TRUE, TokenType.FALSE, TokenType.EOF],
                         [token.type for token in tokens])

    def test_identifiers_and_keyword_boundaries(self):
        tokens = Lexer("letter rule2 _private Score TRUE").tokenize()
        self.assertEqual(["letter", "rule2", "_private", "Score", "TRUE"], [token.lexeme for token in tokens[:-1]])
        self.assertTrue(all(token.type == TokenType.IDENTIFIER for token in tokens[:-1]))

    def test_numbers_and_strings(self):
        tokens = Lexer('0 123 12.50 "hello world" ""').tokenize()
        self.assertEqual([0, 123, 12.5, "hello world", ""], [token.literal for token in tokens[:-1]])
        self.assertIs(int, type(tokens[0].literal))
        self.assertIs(float, type(tokens[2].literal))

    def test_string_escapes(self):
        token = Lexer(r'"line\n\t\"quote\"\\\r"').tokenize()[0]
        self.assertEqual('line\n\t"quote"\\\r', token.literal)

    def test_all_operators_and_delimiters(self):
        tokens = Lexer("+ - * / = == != > >= < <= && || ! ( ) { } ;").tokenize()
        self.assertEqual(
            [TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.EQUAL, TokenType.EQUAL_EQUAL,
             TokenType.BANG_EQUAL, TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS,
             TokenType.LESS_EQUAL, TokenType.AND, TokenType.OR, TokenType.BANG, TokenType.LEFT_PAREN,
             TokenType.RIGHT_PAREN, TokenType.LEFT_BRACE, TokenType.RIGHT_BRACE, TokenType.SEMICOLON, TokenType.EOF],
            [token.type for token in tokens])

    def test_adjacent_tokens_preserve_lexemes_literals_and_positions(self):
        tokens = Lexer("a1==12.5!=2;").tokenize()
        self.assertEqual(
            [(TokenType.IDENTIFIER, "a1", None, 1, 1),
             (TokenType.EQUAL_EQUAL, "==", None, 1, 3),
             (TokenType.NUMBER, "12.5", 12.5, 1, 5),
             (TokenType.BANG_EQUAL, "!=", None, 1, 9),
             (TokenType.NUMBER, "2", 2, 1, 11),
             (TokenType.SEMICOLON, ";", None, 1, 12),
             (TokenType.EOF, "", None, 1, 13)], [(token.type, token.lexeme, token.literal, token.line, token.column)
                                                 for token in tokens],
        )

    def test_comments_whitespace_and_division(self):
        tokens = Lexer(' \t// comment\n 8 / 2; // end').tokenize()
        self.assertEqual([TokenType.NUMBER, TokenType.SLASH, TokenType.NUMBER, TokenType.SEMICOLON, TokenType.EOF],
                         [token.type for token in tokens])
        self.assertEqual((2, 2), (tokens[0].line, tokens[0].column))

    def test_comment_markers_inside_string(self):
        self.assertEqual("https://example", Lexer('"https://example"').tokenize()[0].literal)

    def test_newline_formats_and_eof_location(self):
        for newline in ("\n", "\r\n", "\r"):
            with self.subTest(newline=repr(newline)):
                tokens = Lexer("let x = 1;" + newline + "  print(x);").tokenize()
                self.assertEqual((2, 3), (tokens[5].line, tokens[5].column))
                self.assertEqual((2, 12), (tokens[-1].line, tokens[-1].column))

    def test_empty_source(self):
        tokens = Lexer("").tokenize()
        self.assertEqual(1, len(tokens))
        self.assertEqual(TokenType.EOF, tokens[0].type)
        self.assertEqual((1, 1), (tokens[0].line, tokens[0].column))

    def test_invalid_characters(self):
        for character in ("@", "&", "|", "'", "%", "[", "²"):
            with self.subTest(character=character):
                lexer = Lexer("\n  " + character)
                with self.assertRaisesRegex(LexerError, "line 2, column 3.*Unsupported character"):
                    lexer.tokenize()

    def test_unterminated_strings(self):
        for source in ('"hello', '"hello\nworld"', '"hello' + "\\"):
            with self.subTest(source=source):
                lexer = Lexer(source)
                with self.assertRaisesRegex(LexerError, "Unterminated string"):
                    lexer.tokenize()

    def test_unknown_escape(self):
        lexer = Lexer(r'"bad\q"')
        with self.assertRaisesRegex(LexerError, "Unsupported string escape"):
            lexer.tokenize()

    def test_malformed_and_nonfinite_numbers(self):
        for source in ("1.", "1.2.3", ".5", "9" * 400 + ".0"):
            with self.subTest(source=source[:30]):
                lexer = Lexer(source)
                with self.assertRaises(LexerError):
                    lexer.tokenize()

    def test_incomplete_decimal_reports_number_start(self):
        for suffix in ("", " ", "\n", ";"):
            with self.subTest(suffix=suffix):
                lexer = Lexer("\n  12." + suffix)
                with self.assertRaisesRegex(
                        LexerError, "Expected a digit after decimal point"
                ) as caught:
                    lexer.tokenize()
                self.assertEqual((2, 3), (caught.exception.line, caught.exception.column))


if __name__ == "__main__":
    unittest.main()
