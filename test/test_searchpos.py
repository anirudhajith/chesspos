import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import numpy as np
import chess

from pgn2pos import board_to_bb
import searchpos

def test_bitboard_to_uint8():
	BITBOARD = np.round(np.random.random_sample((773,))).astype(bool)
	BITBOARDS = np.round(np.random.random_sample((2,773))).astype(bool)

	single = searchpos.bitboard_to_uint8(BITBOARD)
	assert single.dtype == np.uint8
	assert single.shape == (1+int(773/8),)

	multiple = searchpos.bitboard_to_uint8(BITBOARDS)
	assert multiple.dtype == np.uint8
	assert multiple.shape == (2,1+int(773/8))

def test_bitboard_to_board():
	FEN = "rnb1kb1r/pp2pppp/2p2n2/3qN3/2pP4/6P1/PP2PP1P/RNBQKB1R w KQkq - 2 6"

	board = chess.Board(FEN)
	bitboard = board_to_bb(board)
	assert bitboard.dtype == bool 
	assert bitboard.shape == (773,)

	reconstructed_board = searchpos.bitboard_to_board(bitboard)
	reconstructed_fen = reconstructed_board.fen()
	assert FEN[:-3] == reconstructed_fen[:-3]
