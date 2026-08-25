import pygame
import sys
import torch
import numpy as np


# Pygame is a library that wraps SDL (Simple DirectMedia Layer), giving us
# a window, an event system, and drawing tools. We import sys in case we
# need to force-exit the process, though pygame.quit() handles most cleanup.


class Board:
    def __init__(self, model):
        
        # pygame.init() starts all pygame subsystems (display, sound, input, etc.)
        # It must be called before anything else in pygame.
        pygame.init()

        self.width_of_window = 800
        self.height_of_window = 800

        # pygame.RESIZABLE lets the user drag the window edges to resize it.
        # The board's square sizes are recalculated each frame to match,
        # so the grid always fills the window correctly.
        self.board = pygame.display.set_mode(
            (self.width_of_window, self.height_of_window), pygame.RESIZABLE
        )
        self.rooklmove = False
        self.rookrmove = False
        self.kingmove = False
        self.b_rooklmove = False
        self.b_rookrmove = False
        self.b_kingmove = False

        self.model = model
        self.humanColor = 1

        

        # get_size() returns the *current* window dimensions as (width, height).
        # We store them here but always refresh in draw_board() because the
        # window can be resized at any time.
        self.x, self.y = self.board.get_size()

        # The Clock object lets us cap the frame rate with clock.tick(fps).
        # Without it the game would run as fast as the CPU allows, wasting resources.
        self.clock = pygame.time.Clock()

        pygame.display.set_caption("Chess")
        self.running = True

        # These are RGB tuples — three values from 0–255 for Red, Green, Blue.
        # These specific colors match a standard tournament chess board.
        self.darkColor = (116, 148, 86)  # green squares
        self.lightColor = (234, 235, 209)  # cream squares
        self.wpBit = 0
        self.bpBit = 0
        for i in range(8):
            self.wpBit |= 1 << (8 + i)
        self.wrBit = (1 << 0) | (1 << 7)
        self.wnBit = (1 << 1) | (1 << 6)
        self.wbBit = (1 << 2) | (1 << 5)
        self.wqBit = 1 << 3
        self.wkBit = 1 << 4
        for i in range(8):
            self.bpBit |= 1 << (48 + i)
        self.brBit = (1 << 56) | (1 << 63)
        self.bnBit = (1 << 57) | (1 << 62)
        self.bbBit = (1 << 58) | (1 << 61)
        self.bqBit = 1 << 59
        self.bkBit = 1 << 60

        # A dictionary to hold loaded piece images, keyed by piece code (e.g. "wp", "bk").
        # Loading images once here is important — loading from disk inside the game
        # loop every frame would be extremely slow.
        self.collideRects = {}
        self.isDragging = False
        self.selectedPiece = None
        self.dragOffset = (0, 0)
        self.selectedPieceSquare = None
        self.image = None
        self.pieceColor = 1

        self.bitBoards = {}
        self.names = self.names = ["bb", "bk", "bn", "bp", "bq", "br", "wb", "wk", "wn", "wp", "wq", "wr"]
        for name in self.names:
            self.bitBoards[name] = getattr(self, name + "Bit", 0)
        # self.bitBoards = {("wp", self.wpBit), ("wr", self.wrBit), ("wn", self.wnBit), ("wb", self.wbBit), ("wq", self.wqBit), ("wk", self.wkBit), ("bp", self.bpBit), ("br", self.brBit), ("bn", self.bnBit), ("bb", self.bbBit), ("bq", self.bqBit), ("bk", self.bkBit)}
        self.piece_images = {}
        
        # print(self.bitBoards)
        self.load_all_pieces()
        self.displayImages()
        # self.startImages()

    def setBoardArray(self):
        self.totalBoard = 0
        for name in self.names:
            val = getattr(self, name + "Bit")
            self.bitBoards[name] = val
            self.totalBoard = self.totalBoard | val
        # self.bitBoards = [self.wpBit, self.wrBit, self.wnBit, self.wbBit, self.wqBit, self.wkBit, self.bpBit, self.brBit, self.bnBit, self.bbBit, self.bqBit, self.bkBit]
        

    def load_all_pieces(self):

        for name in self.names:
            # Load the image and keep it in a dictionary
            self.piece_images[name] = pygame.image.load(f"Assets/neo/neo/{name}.png")

    def draw_board(self):
        # Refresh the current window size in case the user has resized it.
        self.x, self.y = self.board.get_size()

        # Fill the entire window with the light color first.
        # Then we only need to draw the dark squares on top — this is more
        # efficient than drawing all 64 squares individually.
        self.board.fill(self.lightColor)

        # Integer division (//) ensures we get whole-pixel square sizes.
        # Floating-point pixels would cause gaps or overlaps between squares.
        squareWidth = self.x // 8
        squareHeight = self.y // 8

        for i in range(8):  # i = column (file), 0 = left
            for j in range(8):  # j = row (rank), 0 = top
                # A square is dark when the sum of its column and row indices is odd.
                # This is the same checkerboard pattern rule used on a real board.
                if (i + j) % 2 != 0:
                    pygame.draw.rect(
                        self.board,
                        self.darkColor,
                        pygame.Rect(
                            squareWidth * i,  # x position in pixels
                            squareHeight * j,  # y position in pixels
                            squareWidth,
                            squareHeight,
                        ),
                    )

    def run(self):
        # The game loop: keep running until the user closes the window.
        # Each iteration of this loop is one "frame".
        while self.running:
            # pygame collects OS events (clicks, key presses, window close, etc.)
            # into a queue. We must drain the queue every frame, or the window
            # will appear frozen and unresponsive.
            # if (self.pieceColor != self.humanColor):
            #     print(f"\n--- AI is thinking for color {self.pieceColor} ---")
            #     self.draw_board()
            #     self.displayImages()
            #     pygame.display.flip()
            #     pygame.time.wait(500)
            #     ai_move = self.getAIMove()
            #     print(f"AI Move Decided")
            #     self.make_move(ai_move[0], ai_move[1])
                
                
            self.draw_board()
            self.displayImages()

            if self.isDragging and self.draggingPieceName:
                img = self.piece_images[self.draggingPieceName]
                img = pygame.transform.scale(img, (self.x // 8, self.y // 8))
                # Center the piece on the mouse
                self.board.blit(img, (mouse_x - self.x // 16, mouse_y - self.y // 16))

            mouse_x, mouse_y = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    
                    row = mouse_y // (self.y // 8)
                    col = mouse_x // (self.x // 8)
                    clicked_square = (7 - row) * 8 + col 

                    for name, board in self.bitBoards.items():
                        if (board & (1 << clicked_square)):
                            
                            self.isDragging = True
                            self.selectedPieceSquare = clicked_square
                            self.draggingPieceName = name
                            color = self.draggingPieceName[0]
                            if (color == "w"):
                                color = 1
                            else:
                                color = -1
                            if (color != self.humanColor):
                                continue
                            setattr(self, name + "Bit", getattr(self, name + "Bit") & ~(1 << clicked_square))
                            self.setBoardArray() 
                            break
                    if event.button == 1:
                        for name, box in self.collideRects.items():

                            if box.collidepoint(event.pos):
                                self.selectedPiece = box
                                self.isDragging = True
                                row = mouse_y // (self.height_of_window // 8)
                                col = mouse_x // (self.width_of_window // 8)
                                self.selectedPieceSquare = (7 - row) * 8 + col
                                self.image = self.piece_images.get(name[0:2])
                elif event.type == pygame.MOUSEBUTTONUP:
                    if self.isDragging:
                        row = mouse_y // (self.y // 8)
                        col = mouse_x // (self.x // 8)
                        target_square = (7 - row) * 8 + col
                        currentBits = getattr(self, self.draggingPieceName + "Bit")
                        setattr(self, self.draggingPieceName + "Bit", currentBits | (1 << self.selectedPieceSquare))
                        self.setBoardArray()
                        ans = self.make_move(self.selectedPieceSquare, target_square)
                        if (not ans):
                            
                            self.setBoardArray()
                        self.isDragging = False
                        self.draggingPieceName = None

                elif event.type == pygame.MOUSEMOTION:
                    if self.isDragging and self.selectedPiece is not None:
                        self.selectedPiece.x  = mouse_x - (self.selectedPiece.width // 2)
                        self.selectedPiece.y = mouse_y - (self.selectedPiece.height // 2)

            if self.image and self.isDragging:
                self.board.blit(self.image, self.selectedPiece)

            # self.startImages()

            # pygame uses double buffering: draw_board() writes to a back buffer,
            # and flip() swaps it to the screen all at once. This prevents flickering.
            pygame.display.flip()

            # tick(60) sleeps just long enough to cap the loop at 60 frames per second.
            # This keeps CPU usage low while still running smoothly.
            self.clock.tick(60)

        # pygame.quit() shuts down all pygame subsystems cleanly.
        # Always call this before your program exits.
        pygame.quit()

    def drawPiece(self, board, position):
        wpNum = 1
        wnNum = 1
        wrNum = 1
        wbNum = 1
        wqNum = 1
        wkNum = 1
        bpNum = 1
        bnNum = 1
        brNum = 1
        bbNum = 1
        bqNum = 1
        bkNum = 1
        pieceName = ""
        self.x, self.y = self.board.get_size()
        square_w = self.x // 8
        square_h = self.y // 8
        for name, boards in self.bitBoards.items():
            if boards == board:

                original_image = self.piece_images[name]
                image = pygame.transform.scale(original_image, (square_w, square_h))
                self.board.blit(image, (square_w * (position % 8), square_h * (7 - position // 8)))
                if name == "wp":
                    self.collideRects[name + str(wpNum)] = image.get_rect()
                    wpNum += 1
                elif name == "bp":
                    self.collideRects[name + str(bpNum)] = image.get_rect()
                    bpNum += 1
                elif name == "wn":
                    self.collideRects[name + str(wnNum)] = image.get_rect()
                    wnNum += 1
                elif name == "wr":
                    self.collideRects[name + str(wrNum)] = image.get_rect()
                    wrNum += 1
                elif name == "wb":
                    self.collideRects[name + str(wbNum)] = image.get_rect()
                    wbNum += 1
                elif name == "wq":
                    self.collideRects[name + str(wqNum)] = image.get_rect()
                    wqNum += 1
                elif name == "wk":
                    self.collideRects[name + str(wkNum)] = image.get_rect()
                    wkNum += 1
                elif name == "br":
                    self.collideRects[name + str(brNum)] = image.get_rect()
                    brNum += 1
                elif name == "bn":
                    self.collideRects[name + str(bnNum)] = image.get_rect()
                    bnNum += 1
                elif name == "bb":
                    self.collideRects[name + str(bbNum)] = image.get_rect()
                    bbNum += 1
                elif name == "bq":
                    self.collideRects[name + str(bqNum)] = image.get_rect()
                    bqNum += 1
                elif name == "bk":
                    self.collideRects[name + str(bkNum)] = image.get_rect()
                    bkNum += 1

    def pieceName(self, x, y):
        square = x % 8 + y // 8
        for board in self.bitBoards.values():
            if (board & (1 << square)) != 0:
                return self.bitBoards[board]

    def pieceDetermine(self, square):
        # self.setBoardArray()
        # print(self.bitBoards)
        for board in self.bitBoards.values():
            # print(board, type(board))
            if (board & (1 << square)) != 0:
                self.drawPiece(board, square)

    def pieceType(self, square):
        for name, board in self.bitBoards.items():
            if (board & (1 << square)):
                return name


    def boardType(self, square):
        for name, board in self.bitBoards.items():
            if (board & (1 << square)):
                return name







        

    def displayImages(self):
        self.setBoardArray()
        self.x, self.y = self.board.get_size()
        self.totalBoard = self.bbBit | self.bkBit | self.bnBit | self.bqBit | self.bpBit | self.brBit | self.wbBit | self.wkBit | self.wnBit | self.wqBit | self.wpBit | self.wrBit
        for i in range(64):
            if (self.totalBoard & (1 << i)) != 0:
                self.pieceDetermine(i)

    def checkValid(self, pieceSquare, pieceName, target):
        colorMove = pieceName[0:1]

        # 1. Quick Exit: Check if moving the correct color
        if (colorMove == "w" and self.pieceColor == -1) or (
            colorMove == "b" and self.pieceColor == 1
        ):
            return False

        # 2. Pre-calculate Occupancy once per call
        white_occupancy = (
            self.wpBit | self.wrBit | self.wnBit | self.wbBit | self.wqBit | self.wkBit
        )
        black_occupancy = (
            self.bpBit | self.brBit | self.bnBit | self.bbBit | self.bqBit | self.bkBit
        )
        all_occupancy = white_occupancy | black_occupancy

        # 3. Direct Dispatch to the specific color logic
        if colorMove == "w":
            return self._checkValidWhite(
                pieceSquare,
                pieceName,
                target,
                white_occupancy,
                black_occupancy,
                all_occupancy,
            )
        else:
            return self._checkValidBlack(
                pieceSquare,
                pieceName,
                target,
                white_occupancy,
                black_occupancy,
                all_occupancy,
            )

    def _checkValidWhite(
        self,
        pieceSquare,
        pieceName,
        target,
        white_occupancy,
        black_occupancy,
        all_occupancy,
    ):
        if pieceName == "wp":
            if pieceSquare % 8 == 0:
                if pieceSquare == 8:
                    if (
                        target == pieceSquare + 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target - 8)))
                    ):
                        return True
                if (target == pieceSquare + 9 and black_occupancy & (1 << target)) or (
                    target == pieceSquare + 8 and not (all_occupancy & (1 << target))
                ):
                    return True
            elif pieceSquare % 8 == 7:
                if pieceSquare == 15:
                    if (
                        target == pieceSquare + 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target - 8)))
                    ):
                        return True
                if (target == pieceSquare + 7 and black_occupancy & (1 << target)) or (
                    target == pieceSquare + 8 and not (all_occupancy & (1 << target))
                ):
                    return True
            else:
                if pieceSquare / 8 >= 1 and pieceSquare / 8 < 2:
                    if (
                        target == pieceSquare + 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target - 8)))
                    ):
                        return True
                if (target == pieceSquare + 7 and black_occupancy & (1 << target)) or (
                    target == pieceSquare + 9
                    and black_occupancy & (1 << target)
                    or (
                        target == pieceSquare + 8
                        and not (all_occupancy & (1 << target))
                    )
                ):
                    return True

        elif pieceName == "wb":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((pieceSquare % 8) - (target % 8))
            if row_diff != col_diff:
                return False
            if row_diff == 1:
                if not (white_occupancy & (1 << target)):
                    return True

            # Path logic
            direction = 1 if (target - pieceSquare < 0) else 0
            side = 1 if (((target % 8) - (pieceSquare % 8)) < 0) else 0
            if direction == 0:  # up
                if side == 0:  # right
                    for i in range(1, row_diff):
                        bTarget = pieceSquare + (i * 9)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
                else:  # left
                    for i in range(1, row_diff):
                        bTarget = pieceSquare + (i * 7)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
            else:  # down
                if side == 0:  # right
                    for i in range(1, row_diff):
                        bTarget = pieceSquare - (i * 7)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
                else:  # left
                    for i in range(1, row_diff):
                        bTarget = pieceSquare - (i * 9)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False

            if not (white_occupancy & (1 << target)):
                return True

        elif pieceName == "wn":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2):
                if not (white_occupancy & (1 << target)):
                    return True

        elif pieceName == "wr":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if row_diff != 0 and col_diff == 0:  # vertical
                step = 8 if target > pieceSquare else -8
                for i in range(1, row_diff):
                    if all_occupancy & (1 << (pieceSquare + i * step)):
                        return False
                if not (white_occupancy & (1 << target)):
                    return True
            elif row_diff == 0 and col_diff != 0:  # horizontal
                step = 1 if target > pieceSquare else -1
                for i in range(1, col_diff):
                    if all_occupancy & (1 << (pieceSquare + i * step)):
                        return False
                if not (white_occupancy & (1 << target)):
                    return True

        elif pieceName == "wq":
            # Combined slider logic for White
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if not (row_diff == col_diff or row_diff == 0 or col_diff == 0):
                return False
            r_step = 0 if row_diff == 0 else (8 if target > pieceSquare else -8)
            c_step = (
                0 if col_diff == 0 else (1 if (target % 8) > (pieceSquare % 8) else -1)
            )
            for i in range(1, max(row_diff, col_diff)):
                if all_occupancy & (1 << (pieceSquare + i * (r_step + c_step))):
                    return False
            if not (white_occupancy & (1 << target)):
                return True

        elif pieceName == "wk":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            rook_check = (target % 8) - (pieceSquare % 8)
            if rook_check == 2:  # Kingside
                if (
                    (not (all_occupancy & (1 << 5 | 1 << 6)))
                    and self.rookrmove == False
                    and self.kingmove == False
                ):
                    return "w_castles"
            if rook_check == -2:  # Queenside
                if (
                    (not (all_occupancy & (1 << 1 | 1 << 2 | 1 << 3)))
                    and self.rooklmove == False
                    and self.kingmove == False
                ):
                    return "w_castlel"
            if row_diff <= 1 and col_diff <= 1:
                if not (white_occupancy & (1 << target)):
                    return True
        return False

    def _checkValidBlack(
        self,
        pieceSquare,
        pieceName,
        target,
        white_occupancy,
        black_occupancy,
        all_occupancy,
    ):
        if pieceName == "bp":
            if pieceSquare % 8 == 0:
                if pieceSquare == 48:  # Row 6 A-column
                    if (
                        target == pieceSquare - 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target + 8)))
                    ):
                        return True
                if (target == pieceSquare - 7 and white_occupancy & (1 << target)) or (
                    target == pieceSquare - 8 and not (all_occupancy & (1 << target))
                ):
                    return True
            elif pieceSquare % 8 == 7:
                if pieceSquare == 55:  # Row 6 H-column
                    if (
                        target == pieceSquare - 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target + 8)))
                    ):
                        return True
                if (target == pieceSquare - 9 and white_occupancy & (1 << target)) or (
                    target == pieceSquare - 8 and not (all_occupancy & (1 << target))
                ):
                    return True
            else:
                if pieceSquare / 8 >= 6 and pieceSquare / 8 < 7:
                    if (
                        target == pieceSquare - 16
                        and not (all_occupancy & (1 << target))
                        and not (all_occupancy & (1 << (target + 8)))
                    ):
                        return True
                if (target == pieceSquare - 7 and white_occupancy & (1 << target)) or (
                    target == pieceSquare - 9
                    and white_occupancy & (1 << target)
                    or (
                        target == pieceSquare - 8
                        and not (all_occupancy & (1 << target))
                    )
                ):
                    return True

        elif pieceName == "bb":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((pieceSquare % 8) - (target % 8))
            if row_diff != col_diff:
                return False
            if row_diff == 1:
                if not (black_occupancy & (1 << target)):
                    return True

            direction = 1 if (target - pieceSquare < 0) else 0
            side = 1 if (((target % 8) - (pieceSquare % 8)) < 0) else 0
            if direction == 0:  # up
                if side == 0:  # right
                    for i in range(1, row_diff):
                        bTarget = pieceSquare + (i * 9)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
                else:  # left
                    for i in range(1, row_diff):
                        bTarget = pieceSquare + (i * 7)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
            else:  # down
                if side == 0:  # right
                    for i in range(1, row_diff):
                        bTarget = pieceSquare - (i * 7)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
                else:  # left
                    for i in range(1, row_diff):
                        bTarget = pieceSquare - (i * 9)
                        if not (all_occupancy & (1 << bTarget)):
                            continue
                        else:
                            return False
            if not (black_occupancy & (1 << target)):
                return True

        elif pieceName == "bn":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if (row_diff == 2 and col_diff == 1) or (row_diff == 1 and col_diff == 2):
                if not (black_occupancy & (1 << target)):
                    return True

        elif pieceName == "br":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if row_diff != 0 and col_diff == 0:  # vertical
                step = 8 if target > pieceSquare else -8
                for i in range(1, row_diff):
                    if all_occupancy & (1 << (pieceSquare + i * step)):
                        return False
                if not (black_occupancy & (1 << target)):
                    return True
            elif row_diff == 0 and col_diff != 0:  # horizontal
                step = 1 if target > pieceSquare else -1
                for i in range(1, col_diff):
                    if all_occupancy & (1 << (pieceSquare + i * step)):
                        return False
                if not (black_occupancy & (1 << target)):
                    return True

        elif pieceName == "bq":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            if not (row_diff == col_diff or row_diff == 0 or col_diff == 0):
                return False
            r_step = 0 if row_diff == 0 else (8 if target > pieceSquare else -8)
            c_step = (
                0 if col_diff == 0 else (1 if (target % 8) > (pieceSquare % 8) else -1)
            )
            for i in range(1, max(row_diff, col_diff)):
                if all_occupancy & (1 << (pieceSquare + i * (r_step + c_step))):
                    return False
            if not (black_occupancy & (1 << target)):
                return True

        elif pieceName == "bk":
            row_diff = abs((target // 8) - (pieceSquare // 8))
            col_diff = abs((target % 8) - (pieceSquare % 8))
            rook_check = (target % 8) - (pieceSquare % 8)
            if rook_check == 2:  # Kingside (f8, g8 squares 61, 62)
                if (
                    (not (all_occupancy & (1 << 61 | 1 << 62)))
                    and self.rookrmove == False
                    and self.kingmove == False
                ):
                    return "b_castles"
            if rook_check == -2:  # Queenside (b8, c8, d8 squares 57, 58, 59)
                if (
                    (not (all_occupancy & (1 << 57 | 1 << 58 | 1 << 59)))
                    and self.rooklmove == False
                    and self.kingmove == False
                ):
                    return "b_castlel"
            if row_diff <= 1 and col_diff <= 1:
                if not (black_occupancy & (1 << target)):
                    return True
        return False

    # def checkValid(self, pieceSquare, pieceName, target):
    #     colorMove = pieceName[0:1]
    #     print(colorMove)
    #     if (colorMove == "w" and self.pieceColor == -1) or (
    #         colorMove == "b" and self.pieceColor == 1
    #     ):
    #         return False
    #     white_occupancy = (self.wpBit | self.wrBit | self.wnBit | self.wbBit | self.wqBit | self.wkBit)
    #     black_occupancy = (self.bpBit | self.brBit | self.bnBit | self.bbBit | self.bqBit | self.bkBit)
    #     all_occupancy = white_occupancy | black_occupancy
    #     if pieceName == "wp":
    #         if pieceSquare % 8 == 0:
    #             if (pieceSquare == 8):
    #                 if (target == pieceSquare + 16 and not (all_occupancy & (1 << target)) and not (all_occupancy & (1 << (target - 8)))):
    #                     return True
    #             if (target == pieceSquare + 9 and black_occupancy & (1 << target)) or (target == pieceSquare + 8 and not (all_occupancy & (1 << target))):
    #                 return True
    #         elif pieceSquare % 8 == 7:
    #             if (pieceSquare == 15):
    #                 if (target == pieceSquare + 16 and not (all_occupancy & (1 << target)) and not (all_occupancy & (1 << (target - 8)))):
    #                     return True
    #             if (target == pieceSquare + 7 and black_occupancy & (1 << target)) or (target == pieceSquare + 8 and not (all_occupancy & (1 << target))):
    #                 return True
    #         else:
    #             if (pieceSquare / 8 >= 1 and pieceSquare / 8 < 2):
    #                 if (target == pieceSquare + 16 and not (all_occupancy & (1 << target)) and not (all_occupancy & (1 << (target - 8)))):
    #                     return True
    #             if (target == pieceSquare + 7 and black_occupancy & (1 << target)) or (target == pieceSquare + 9 and black_occupancy & (1 << target) or (target == pieceSquare + 8 and not (all_occupancy & (1 << target)))):
    #                 return True

    #     elif pieceName == "wb":
    #         side = 2
    #         direction = 2
    #         row_diff = abs((target // 8) - (pieceSquare // 8))
    #         col_diff = abs((pieceSquare % 8) - (target % 8))
    #         if (row_diff != col_diff):
    #             return False
    #         if (row_diff == 1):
    #             if (not (white_occupancy & (1 << target))):
    #                 return True
    #         if (row_diff == col_diff):
    #             # 0 = up, 1 = down
    #             if (target - pieceSquare < 0):
    #                 direction = 1
    #             else:
    #                 direction = 0
    #             if (((target % 8) - (pieceSquare % 8)) < 0):
    #                 side = 1
    #             else:
    #                 side = 0
    #             # up
    #             if (direction == 0):
    #                 # right
    #                 if (side == 0):
    #                     for i in range(1, row_diff):
    #                         bTarget = pieceSquare + (i * 9)
    #                         if ((bTarget - pieceSquare) % 9 == 0 and not (all_occupancy & (1 << bTarget))):
    #                             continue
    #                         else:
    #                             return False
    #                 # left
    #                 else:
    #                     for i in range(1, row_diff):
    #                         bTarget = pieceSquare + (i * 7)
    #                         if ((pieceSquare - bTarget) % 7 == 0 and not (all_occupancy & (1 << bTarget))):
    #                             continue
    #                         else:
    #                             return False

    #             # down
    #             else:
    #                 # right
    #                 if (side == 0):
    #                     for i in range(1, row_diff):
    #                         bTarget = pieceSquare - (i * 7)
    #                         if ((pieceSquare - bTarget) % 7 == 0 and not (all_occupancy & (1 << bTarget))):
    #                             continue
    #                         else:
    #                             return False
    #                 else:
    #                     for i in range(1, row_diff):
    #                         bTarget = pieceSquare - (i * 9)
    #                         if ((pieceSquare - bTarget) % 9 == 0 and not (all_occupancy & (1 << bTarget))):
    #                             continue
    #                         else:
    #                             return False
    #         if (((target - pieceSquare) % 7 == 0 or (pieceSquare - target) % 7 == 0) and not (white_occupancy & (1 << target))):
    #             return True
    #         if (((target - pieceSquare) % 9 == 0 or (pieceSquare - target) % 9 == 0) and not (white_occupancy & (1 << target))):
    #             return True

    #     elif pieceName == "wn":
    #         row_diff = abs((target // 8) - (pieceSquare // 8))
    #         col_diff = abs((target % 8) - (pieceSquare % 8))
    #         if (row_diff == 2):
    #             # print('hi')
    #             if (col_diff != 1):
    #                 return False
    #             else:
    #                 if (not (white_occupancy & (1 << target))):
    #                     return True
    #         if (col_diff == 2):
    #             if (row_diff != 1):
    #                 return False
    #             else:
    #                 if (not (white_occupancy & (1 << target))):
    #                     return True
    #     elif pieceName == "wr":
    #         direction = 2
    #         row_diff = abs((target // 8) - (pieceSquare // 8))
    #         col_diff = abs((target % 8) - (pieceSquare % 8))
    #         if (row_diff != 0):
    #             if (col_diff == 0):
    #                 if (row_diff == 1):
    #                     if (not (white_occupancy & (1 << target))):
    #                         return True
    #                 # down
    #                 if ((target // 8) - (pieceSquare // 8) < 0):
    #                     for i in range(1, row_diff):
    #                         rTarget = pieceSquare - (i * 8)
    #                         if ((rTarget - pieceSquare) % 8 == 0 and not (all_occupancy & (1 << rTarget))):
    #                             continue
    #                         else:
    #                             return False
    #                 # up
    #                 if ((target // 8) - (pieceSquare // 8) > 0):
    #                     for i in range(1, row_diff):
    #                         rTarget = pieceSquare + (i * 8)
    #                         if ((rTarget - pieceSquare) % 8 == 0 and not (all_occupancy & (1 << rTarget))):
    #                             continue
    #                         else:
    #                             return False

    #             else:
    #                 return False
    #         if (col_diff != 0):
    #             if (row_diff == 0):
    #                 if (col_diff == 1):
    #                     if (not (white_occupancy & (1 << target))):
    #                         return True
    #                 # left
    #                 if ((target % 8) - (pieceSquare % 8) < 0):
    #                     for i in range(1, col_diff):
    #                         rTarget = pieceSquare - i
    #                         if (not (all_occupancy & (1 << rTarget))):
    #                             continue
    #                         else:
    #                             return False
    #                 # right
    #                 elif ((target % 8) - (pieceSquare % 8) > 0):
    #                     for i in range(1, col_diff):
    #                         rTarget = pieceSquare + i
    #                         if (not (all_occupancy & (1 << rTarget))):
    #                             continue
    #                         else:
    #                             return False
    #                 else:
    #                     return False

    #         if ((abs(target - pieceSquare) % 8 == 0) and not (white_occupancy & (1 << target))):
    #             return True
    #         if ((target // 8 == pieceSquare // 8) and not (white_occupancy & (1 << target))):
    #             return True
    #     elif pieceName == "wq":
    #         row_diff = abs((target // 8) - (pieceSquare // 8))
    #         col_diff = abs((target % 8) - (pieceSquare % 8))
    #         if ((row_diff > 0 and col_diff > 0) and (row_diff == col_diff)):
    #             side = 2
    #             direction = 2
    #             if (row_diff != col_diff):
    #                 return False
    #             if (row_diff == 1):
    #                 if (not (white_occupancy & (1 << target))):
    #                     return True
    #             if (row_diff == col_diff):
    #                 # 0 = up, 1 = down
    #                 if (target - pieceSquare < 0):
    #                     direction = 1
    #                 else:
    #                     direction = 0
    #                 if (((target % 8) - (pieceSquare % 8)) < 0):
    #                     side = 1
    #                 else:
    #                     side = 0
    #                 # up
    #                 if (direction == 0):
    #                     # right
    #                     if (side == 0):
    #                         for i in range(1, row_diff):
    #                             bTarget = pieceSquare + (i * 9)
    #                             if ((bTarget - pieceSquare) % 9 == 0 and not (all_occupancy & (1 << bTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #                     # left
    #                     else:
    #                         for i in range(1, row_diff):
    #                             bTarget = pieceSquare + (i * 7)
    #                             if ((pieceSquare - bTarget) % 7 == 0 and not (all_occupancy & (1 << bTarget))):
    #                                 continue
    #                             else:
    #                                 return False

    #                 # down
    #                 else:
    #                     # right
    #                     if (side == 0):
    #                         for i in range(1, row_diff):
    #                             bTarget = pieceSquare - (i * 7)
    #                             if ((pieceSquare - bTarget) % 7 == 0 and not (all_occupancy & (1 << bTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #                     else:
    #                         for i in range(1, row_diff):
    #                             bTarget = pieceSquare - (i * 9)
    #                             if ((pieceSquare - bTarget) % 9 == 0 and not (all_occupancy & (1 << bTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #             if (((target - pieceSquare) % 7 == 0 or (pieceSquare - target) % 7 == 0) and not (white_occupancy & (1 << target))):
    #                 return True
    #             if (((target - pieceSquare) % 9 == 0 or (pieceSquare - target) % 9 == 0) and not (white_occupancy & (1 << target))):
    #                 return True
    #         elif ((row_diff > 0 and col_diff == 0) or (row_diff == 0 and col_diff > 0)):
    #             direction = 2

    #             if (row_diff != 0):
    #                 if (col_diff == 0):
    #                     if (row_diff == 1):
    #                         if (not (white_occupancy & (1 << target))):
    #                             return True
    #                     # down
    #                     if ((target // 8) - (pieceSquare // 8) < 0):
    #                         for i in range(1, row_diff):
    #                             rTarget = pieceSquare - (i * 8)
    #                             if ((rTarget - pieceSquare) % 8 == 0 and not (all_occupancy & (1 << rTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #                     # up
    #                     if ((target // 8) - (pieceSquare // 8) > 0):
    #                         for i in range(1, row_diff):
    #                             rTarget = pieceSquare + (i * 8)
    #                             if ((rTarget - pieceSquare) % 8 == 0 and not (all_occupancy & (1 << rTarget))):
    #                                 continue
    #                             else:
    #                                 return False

    #                 else:
    #                     return False
    #             if (col_diff != 0):
    #                 if (row_diff == 0):
    #                     if (col_diff == 1):
    #                         if (not (white_occupancy & (1 << target))):
    #                             return True
    #                     # left
    #                     if ((target % 8) - (pieceSquare % 8) < 0):
    #                         for i in range(1, col_diff):
    #                             rTarget = pieceSquare - i
    #                             if (not (all_occupancy & (1 << rTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #                     # right
    #                     elif ((target % 8) - (pieceSquare % 8) > 0):
    #                         for i in range(1, col_diff):
    #                             rTarget = pieceSquare + i
    #                             if (not (all_occupancy & (1 << rTarget))):
    #                                 continue
    #                             else:
    #                                 return False
    #                     else:
    #                         return False

    #             if ((abs(target - pieceSquare) % 8 == 0) and not (white_occupancy & (1 << target))):
    #                 return True
    #             if ((target // 8 == pieceSquare // 8) and not (white_occupancy & (1 << target))):
    #                 return True
    #         else:
    #             return False

    #     elif pieceName == "wk":
    #         row_diff = abs((target // 8) - (pieceSquare // 8))
    #         col_diff = abs((target % 8) - (pieceSquare % 8))
    #         rook_check = (target % 8) - (pieceSquare % 8)
    #         print(rook_check)
    #         if (rook_check == 2):
    #             if ((not (all_occupancy & (1 << 5 | 1 << 6))) and self.rookrmove == False and self.kingmove == False):
    #                 return "castles"
    #         if (rook_check == -2):
    #             if ((not (all_occupancy & (1 << 1 | 1 << 2 | 1 << 3))) and self.rooklmove == False and self.kingmove == False):
    #                 return "castlel"
    #         if (row_diff > 1 or col_diff > 1):
    #             return False
    #         if (not (white_occupancy & (1 << target))):

    #             return True

    def startImages(self):
        self.x, self.y = self.board.get_size()
        square_w = self.x // 8
        square_h = self.y // 8
        names = [
            "bb.png",
            "bk.png",
            "bn.png",
            "bp.png",
            "bq.png",
            "br.png",
            "wp.png",
            "wk.png",
            "wq.png",
            "wr.png",
            "wn.png",
            "wb.png",
        ]
        for name, original_image in self.piece_images.items():

            # 2. CREATE the scaled version
            image = pygame.transform.scale(original_image, (square_w, square_h))
            if name.startswith("w"):
                if name.startswith("wp"):
                    for i in range(8):
                        self.board.blit(image, (square_w * i, square_h * 6))
                else:
                    if "wr" in name:
                        self.board.blit(image, (square_w * 0, square_h * 7))  # A1
                        self.board.blit(image, (square_w * 7, square_h * 7))  # H1

                    elif "wn" in name:
                        self.board.blit(image, (square_w * 1, square_h * 7))  # B1
                        self.board.blit(image, (square_w * 6, square_h * 7))  # G1

                    elif "wb" in name:
                        self.board.blit(image, (square_w * 2, square_h * 7))  # C1
                        self.board.blit(image, (square_w * 5, square_h * 7))  # F1

                    elif "wq" in name:
                        self.board.blit(image, (square_w * 3, square_h * 7))  # D1

                    elif "wk" in name:
                        self.board.blit(image, (square_w * 4, square_h * 7))  # E1
            else:
                if name.startswith("bp"):
                    for i in range(8):
                        self.board.blit(image, (square_w * i, square_h * 1))
                elif "br" in name:
                    self.board.blit(image, (square_w * 0, square_h * 0))  # A8
                    self.board.blit(image, (square_w * 7, square_h * 0))  # H8
                elif "bn" in name:
                    self.board.blit(image, (square_w * 1, square_h * 0))  # B8
                    self.board.blit(image, (square_w * 6, square_h * 0))  # G8
                elif "bb" in name:
                    self.board.blit(image, (square_w * 2, square_h * 0))  # C8
                    self.board.blit(image, (square_w * 5, square_h * 0))  # F8
                elif "bq" in name:
                    self.board.blit(image, (square_w * 3, square_h * 0))  # D8
                elif "bk" in name:
                    self.board.blit(image, (square_w * 4, square_h * 0))  # E8

    def drawBit(self):
        self.wpBit = 1
        self.wrBit = 1



    def get_all_legal_moves(self):
        legal_moves = []
        # 1. Identify whose turn it is and collect their pieces
        if self.pieceColor == 1:
            friendly_pieces = ["wp", "wr", "wn", "wb", "wq", "wk"]
            enemy_occupancy = self.bpBit | self.brBit | self.bnBit | self.bbBit | self.bqBit | self.bkBit
            friendly_occupancy = self.wpBit | self.wrBit | self.wnBit | self.wbBit | self.wqBit | self.wkBit
        else:
            friendly_pieces = ["bp", "br", "bn", "bb", "bq", "bk"]
            enemy_occupancy = self.wpBit | self.wrBit | self.wnBit | self.wbBit | self.wqBit | self.wkBit
            friendly_occupancy = self.bpBit | self.brBit | self.bnBit | self.bbBit | self.bqBit | self.bkBit

        # 2. Iterate through all squares and find friendly pieces
        for start_square in range(64):
            piece_name = None
            for p in friendly_pieces:
                if getattr(self, p + "Bit") & (1 << start_square):
                    piece_name = p
                    break
            
            if piece_name:
                # 3. Use your existing checkValid logic to find potential targets
                # (This is a bit slow but ensures consistency with your rules)
                for target_square in range(64):
                    if self.checkValid(start_square, piece_name, target_square):
                        # 4. Check if the move leaves the King in check
                        if not self.leaves_king_in_check(start_square, piece_name, target_square):
                            legal_moves.append((start_square, target_square))
        return legal_moves

    def leaves_king_in_check(self, start, piece, target):
        # Save current state
        original_state = {name: getattr(self, name + "Bit") for name in self.names}
        original_color = self.pieceColor

        # "Make" the move temporarily
        # (This is a simplified version - doesn't handle all captures/castling logic perfectly)
        setattr(self, piece + "Bit", getattr(self, piece + "Bit") & ~(1 << start) | (1 << target))
        # Remove enemy piece if captured
        for p in self.names:
            if p != piece:
                setattr(self, p + "Bit", getattr(self, p + "Bit") & ~(1 << target))

        # Check if King is attacked
        king_name = "wk" if original_color == 1 else "bk"
        king_square = bin(getattr(self, king_name + "Bit")).count('0', bin(getattr(self, king_name + "Bit")).find('1')) # Bit index
        
        # We need an "is_attacked" check here
        in_check = self.is_square_attacked(king_square, -original_color)

        # "Unmake" the move
        for name, bit in original_state.items():
            setattr(self, name + "Bit", bit)
        self.pieceColor = original_color
        
        return in_check


    def check_game_status(self):
        moves = self.get_all_legal_moves()
        
        if len(moves) == 0:
            # Determine King square
            king_name = "wk" if self.pieceColor == 1 else "bk"
            king_bitboard = getattr(self, king_name + "Bit")
            # Find the index of the 1 bit
            king_square = (king_bitboard & -king_bitboard).bit_length() - 1

            if self.is_square_attacked(king_square, -self.pieceColor):
                return "CHECKMATE" # Current player lost
            else:
                return "STALEMATE" # Draw
        
        return "IN_PROGRESS"

    def is_square_attacked(self, square, attacker_color):
        # Temporarily swap turn to see if the enemy can "legally" move to this square
        original_color = self.pieceColor
        self.pieceColor = attacker_color
        
        attacker_pieces = ["wp", "wr", "wn", "wb", "wq", "wk"] if attacker_color == 1 else ["bp", "br", "bn", "bb", "bq", "bk"]
        
        for p in attacker_pieces:
            bitboard = getattr(self, p + "Bit")
            for start_sq in range(64):
                if bitboard & (1 << start_sq):
                    # If any enemy piece can legally "capture" the square
                    if self.checkValid(start_sq, p, square):
                        self.pieceColor = original_color
                        return True
        
        self.pieceColor = original_color
        return False



    def createMatrix(self):
        wp_array = np.array([self.wpBit], dtype=np.uint64).view(np.uint8)
        wp = np.unpackbits(wp_array, bitorder='little').reshape(8, 8)
        wr_array = np.array([self.wrBit], dtype=np.uint64).view(np.uint8)
        wr = np.unpackbits(wr_array, bitorder='little').reshape(8, 8)
        wn_array = np.array([self.wnBit], dtype=np.uint64).view(np.uint8)
        wn = np.unpackbits(wn_array, bitorder='little').reshape(8, 8)
        wb_array = np.array([self.wbBit], dtype=np.uint64).view(np.uint8)
        wb = np.unpackbits(wb_array, bitorder='little').reshape(8, 8)
        wk_array = np.array([self.wkBit], dtype=np.uint64).view(np.uint8)
        wk = np.unpackbits(wk_array, bitorder='little').reshape(8, 8)
        wq_array = np.array([self.wqBit], dtype=np.uint64).view(np.uint8)
        wq = np.unpackbits(wq_array, bitorder='little').reshape(8, 8)
        bp_array = np.array([self.bpBit], dtype=np.uint64).view(np.uint8)
        bp = np.unpackbits(bp_array, bitorder='little').reshape(8, 8)
        br_array = np.array([self.brBit], dtype=np.uint64).view(np.uint8)
        br = np.unpackbits(br_array, bitorder='little').reshape(8, 8)
        bn_array = np.array([self.bnBit], dtype=np.uint64).view(np.uint8)
        bn = np.unpackbits(bn_array, bitorder='little').reshape(8, 8)
        bb_array = np.array([self.bbBit], dtype=np.uint64).view(np.uint8)
        bb = np.unpackbits(bb_array, bitorder='little').reshape(8, 8)
        bk_array = np.array([self.bkBit], dtype=np.uint64).view(np.uint8)
        bk = np.unpackbits(bk_array, bitorder='little').reshape(8, 8)
        bq_array = np.array([self.bqBit], dtype=np.uint64).view(np.uint8)
        bq = np.unpackbits(bq_array, bitorder='little').reshape(8, 8)
        
        if self.pieceColor == 1:
            move_array = np.full((8, 8), 1)
        else:
            move_array = np.full((8, 8), 0)



        return np.stack([wp, wr, wn, wb, wk, wq, bp, br, bn, bb, bk, bq, move_array])
        


    def createCurrentBoards(self, allBoards):
        currentBitboards = {}
        for nowBoard in allBoards:
            currentBitboards[nowBoard] = getattr(self, nowBoard + "Bit")
        return currentBitboards

    def make_move(self, start_square, target_square):
        piece = self.pieceType(start_square)
        if (piece == None):
            return False
            
        ans = self.checkValid(start_square, piece, target_square)
        if (not ans):
            return False

        if (ans == "w_castles"):
            self.wrBit &= ~(1 << 7)
            self.wrBit |= (1 << 5)
            self.wkBit &= ~(1 << 4)
            self.wkBit |= (1 << 6)
            self.kingmove = True
            self.rookrmove = True
            setattr(self, "wrBit", self.wrBit)
            setattr(self, "wkBit", self.wkBit)
        elif (ans == "w_castlel"):
            self.wrBit &= ~(1 << 0)
            self.wrBit |= (1 << 3)
            self.wkBit &= ~(1 << 4)
            self.wkBit |= (1 << 2)
            self.kingmove = True
            self.rooklmove = True
            setattr(self, "wrBit", self.wrBit)
            setattr(self, "wkBit", self.wkBit)
        elif (ans == "b_castles"):
            self.brBit &= ~(1 << 63)
            self.brBit |= (1 << 61)
            self.bkBit &= ~(1 << 60)
            self.bkBit |= (1 << 62)
            self.b_kingmove = True
            self.b_rookrmove = True
            setattr(self, "brBit", self.brBit)
            setattr(self, "bkBit", self.bkBit)
        elif (ans == "b_castlel"):
            self.brBit &= ~(1 << 56)
            self.brBit |= (1 << 59)
            self.bkBit &= ~(1 << 60)
            self.bkBit |= (1 << 58)
            self.b_kingmove = True
            self.b_rooklmove = True
            setattr(self, "brBit", self.brBit)
            setattr(self, "bkBit", self.bkBit)
        else:
            board = self.boardType(target_square)
            if (board != None):
                self.bitBoards[board] &= ~(1 << target_square)
                setattr(self, board + "Bit", self.bitBoards[board])

            self.bitBoards[piece] &= ~(1 << start_square)
            rank = target_square // 8
            if (piece == "wp" and rank == 7):
                self.bitBoards["wq"] |= (1 << target_square)
                setattr(self, "wqBit", self.bitBoards["wq"])
            elif (piece == "bp" and rank == 0):
                self.bitBoards["bq"] |= (1 << target_square)
                setattr(self, "bqBit", self.bitBoards["bq"])
            else:
                self.bitBoards[piece] |= (1 << target_square)
            
            setattr(self, piece + "Bit", self.bitBoards[piece])

            if (piece == "wk"):
                self.kingmove = True
            elif (piece == "bk"):
                self.b_kingmove = True
            elif (piece == "wr"):
                if (start_square == 0): self.rooklmove = True
                if (start_square == 7): self.rookrmove = True
            elif (piece == "br"):
                if (start_square == 56): self.b_rooklmove = True
                if (start_square == 63): self.b_rookrmove = True

        self.pieceColor *= -1
        self.setBoardArray()
        return True
        

        
        



    def switchColor(self):
        self.pieceColor *= -1


    def setBoards(self, boards):
        allBoards = ["wp", "wr", "wn", "wb", "wq", "wk", "bp", "br", "bn", "bb", "bq", "bk"]
        for board in allBoards:
            setattr(self, board + "Bit", boards[board])
    
    def getBoards(self):
        allBoards = ["wp", "wr", "wn", "wb", "wq", "wk", "bp", "br", "bn", "bb", "bq", "bk"]
        return allBoards



    def get_all_legal_moves(self):
        legal_moves = []
        allBoards = ["wp", "wr", "wn", "wb", "wq", "wk", "bp", "br", "bn", "bb", "bq", "bk"]
        white_pieces = ["wp", "wr", "wn", "wb", "wq", "wk"]
        black_pieces = ["bp", "br", "bn", "bb", "bq", "bk"]

        currentBitboards = {}
        
        

        if (self.pieceColor == 1):
            current_pieces = white_pieces
            current_board = self.wpBit | self.wrBit | self.wnBit | self.wbBit | self.wqBit | self.wkBit
        else:
            current_pieces = black_pieces
            current_board = self.bpBit | self.brBit | self.bnBit | self.bbBit | self.bqBit | self.bkBit

        
        
        for i in range(64):
            if (current_board & (1 << i)):
                for board in current_pieces:
                    var_name = board + "Bit"
                    currentVal = getattr(self, var_name)
                    if (currentVal & (1 << i)):
                        pieceName = board
                for j in range(64):
                    if (self.checkValid(i, pieceName, j)):
                        currentBitboards = self.createCurrentBoards(allBoards)
                        self.make_move(i, j)
                        in_check = False
                        
                        if (self.pieceColor == 1):
                            kingLoc = self.bkBit.bit_length() - 1
                        else:
                            kingLoc = self.wkBit.bit_length() - 1
                        
                        if (self.pieceColor == 1):
                            enemy_board = white_pieces
                        else:
                            enemy_board = black_pieces

                        
                        for s in range(64):
                            for enemyBoard in enemy_board:
                                enemy_name = enemyBoard + "Bit"
                                currentEnemy = getattr(self, enemy_name)
                                if (currentEnemy & (1 << s)):
                                    enemyPiece = enemyBoard
                                    if (self.checkValid(s, enemyPiece, kingLoc)):
                                        in_check = True
                                        break
                            if (in_check):
                                break
                            
                        
                        for nowBoard in allBoards:
                            setattr(self, nowBoard + "Bit", currentBitboards[nowBoard])
                        self.setBoardArray()
                        self.pieceColor *= -1
                        if (not (in_check)):
                            legal_moves.append((i, j))
                        
                        
                        
                        
                        


                

            



        return legal_moves


    # def getAIMove(self):
    #     moveCount = 0
    #     moves = self.get_all_legal_moves()
        
        
    #     if (not moves):
    #         return (None, None)
    #     scores = []
    #     for start, target in moves:
    #         moveCount += 1
    #         if (moveCount % 5 == 0):
    #             print(f"Evaluating move {moveCount}/{len(moves)}...")
    #         outScores = []
    #         currentBoards = self.createCurrentBoards(self.getBoards())
    #         self.make_move(start, target)
    #         if (self.check_game_status() == "CHECKMATE"):
    #             scores.append(999)
    #             self.setBoards(currentBoards)
    #             self.setBoardArray()
    #             self.switchColor()
    #             continue
    #         elif (self.check_game_status() == "DRAW"):
    #             scores.append(0)
    #             self.setBoards(currentBoards)
    #             self.setBoardArray()
    #             self.switchColor()
    #             continue
    #         opponentMoves = self.get_all_legal_moves()
    #         for outStart, outTarget in opponentMoves:
    #             secondBoards = self.createCurrentBoards(self.getBoards())
    #             self.make_move(outStart, outTarget)
    #             if (self.check_game_status() == "CHECKMATE"):
    #                 outScores.append(-999)
    #                 self.setBoards(secondBoards)
    #                 self.setBoardArray()
    #                 self.switchColor()
    #                 continue
    #             elif (self.check_game_status() == "DRAW"):
    #                 outScores.append(0)
    #                 self.setBoards(secondBoards)
    #                 self.setBoardArray()
    #                 self.switchColor()
    #                 continue
    #             opponentMoves2 = self.get_all_legal_moves()
    #             inScores = []
    #             for inStart, inTarget in opponentMoves2:
    #                 thirdBoards = self.createCurrentBoards(self.getBoards())
    #                 self.make_move(inStart, inTarget)
    #                 if (self.check_game_status() == "CHECKMATE"):
    #                     inScores.append(999)
    #                     self.setBoards(thirdBoards)
    #                     self.setBoardArray()
    #                     self.switchColor()
    #                     continue
    #                 elif (self.check_game_status() == "DRAW"):
    #                     inScores.append(0)
    #                     self.setBoards(thirdBoards)
    #                     self.setBoardArray()
    #                     self.switchColor()
    #                     continue


    #                 matrix = self.createMatrix()
    #                 tens = torch.from_numpy(matrix)
    #                 tens = tens.float()
    #                 tens = torch.unsqueeze(tens, 0)
    #                 with torch.no_grad():
    #                     score = self.model(tens)
    #                 inScores.append(score.item())
    #                 self.setBoards(thirdBoards)
    #                 self.setBoardArray()
    #                 self.switchColor()
    #             if inScores:
    #                 outScores.append(max(inScores))
    #             elif (self.check_game_status() == "CHECKMATE"):
    #                 outScores.append(-999)
    #             self.setBoards(secondBoards)
    #             self.setBoardArray()
    #             self.switchColor()
    #         if outScores:
    #             worst_case = min(outScores)
    #             scores.append(worst_case)
        
        
            
    #         #scores.append(worst_case)
    #         self.setBoards(currentBoards)
    #         self.setBoardArray()
    #         self.switchColor()
    #     bestMove = np.argmax(scores)
        
    #     return moves[bestMove]

    def getAIMove(self):
        moveCount = 0
        moves = self.get_all_legal_moves()
        aiSide = self.pieceColor
        
        if (not moves):
            return (None, None)
            
        scores = []
        for start, target in moves:
            moveCount += 1
            if (moveCount % 5 == 0):
                print(f"Evaluating move {moveCount}/{len(moves)}...")
                
            outScores = []
            currentBoards = self.createCurrentBoards(self.getBoards())
            self.make_move(start, target)
            
            # 1. Outer Loop Checkmate/Draw Check
            if (self.check_game_status() == "CHECKMATE"):
                scores.append(999)
                self.setBoards(currentBoards)
                self.setBoardArray()
                self.switchColor()
                continue
            elif (self.check_game_status() == "DRAW"):
                scores.append(0)
                self.setBoards(currentBoards)
                self.setBoardArray()
                self.switchColor()
                continue

            opponentMoves = self.get_all_legal_moves()
            for outStart, outTarget in opponentMoves:
                secondBoards = self.createCurrentBoards(self.getBoards())
                self.make_move(outStart, outTarget)
                
                # 2. Inner Loop Checkmate/Draw Check
                if (self.check_game_status() == "CHECKMATE"):
                    outScores.append(-999)
                elif (self.check_game_status() == "DRAW"):
                    outScores.append(0)
                else:
                    # 3. Model Evaluation happens at the end of the 2nd move
                    matrix = self.createMatrix()
                    tens = torch.from_numpy(matrix)
                    tens = tens.float()
                    tens = torch.unsqueeze(tens, 0)
                    with torch.no_grad():
                        score = self.model(tens).item()
                    material_score = self.materialScore() / 10.0
                    total_score = score + material_score
                    if (aiSide == 1):
                        if (self.inCheck(1, "bk")):
                            total_score += 0.5
                        if (self.inCheck(-1, "wk")):
                            total_score -= 0.5
                    elif (aiSide== -1):
                        if (self.inCheck(1, "bk")):
                            total_score -= 0.5
                        if (self.inCheck(-1, "wk")):
                            total_score += 0.5
                    
                    outScores.append(total_score)
                    
                
                # Undo opponent move
                self.setBoards(secondBoards)
                self.setBoardArray()
                self.switchColor()

            # 4. Handoff: The value of your move is the opponent's best response
            if outScores:
                if (self.pieceColor == -1): # If opponent is Black
                    worst_case = min(outScores)
                else: # If opponent is White
                    worst_case = max(outScores)
                scores.append(worst_case)
            else:
                scores.append(0)

            # Undo your move
            self.setBoards(currentBoards)
            self.setBoardArray()
            self.switchColor()

        # 5. Final Decision
        if (self.pieceColor == 1):
            bestMoveIdx = np.argmax(scores)
        else:
            bestMoveIdx = np.argmin(scores)
            
        return moves[bestMoveIdx]



    def inCheck(self, attkColor, kingName):
        
        kingBit = getattr(self, kingName + "Bit")
        kingBit = (kingBit & -kingBit).bit_length() - 1
        if (self.is_square_attacked(kingBit, attkColor)):
            return True
        return False

    def materialScore(self):
        wScore = 0
        bScore = 0

        for name, bit in self.bitBoards.items():
            if name == "wp":
                wScore += 1 * bit.bit_count()
            elif name == "wn" or name == "wb":
                wScore += 3 * bit.bit_count()
            elif name == "wr":
                wScore += 5 * bit.bit_count()
            elif name == "wq":
                wScore += 9 * bit.bit_count()
            elif name == "wk":
                wScore += 1000 * bit.bit_count()
            elif name == "bp":
                bScore += 1 * bit.bit_count()
            elif name == "bn" or name == "bb":
                bScore += 3 * bit.bit_count()
            elif name == "br":
                bScore += 5 * bit.bit_count()
            elif name == "bq":
                bScore += 9 * bit.bit_count()
            elif name == "bk":
                bScore += 1000 * bit.bit_count()
            
        return wScore - bScore


    def promotion(self, location):
        return True




    
    
                    

            
        




        



if __name__ == "__main__":
    # This guard means the game only runs when you execute this file directly.
    # If another file imports board.py, this block is skipped — useful later
    # when main.py becomes the proper entry point.
    model = 3
    game = Board(model)
    
    game.run()
