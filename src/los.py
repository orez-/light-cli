# http://playtechs.blogspot.ca/2007/03/2d-portal-visibility-part-1.html

portals = [[   1,  1,   1, -1,   1,  0 ],
           [  -1,  1,   1,  1,   0,  1 ],
           [  -1, -1,  -1,  1,  -1,  0 ],
           [   1, -1,  -1, -1,   0, -1 ]]

def a_right_of_b(ax, ay, bx, by):
    return ax * by > ay * bx

class Visibility(object):
    def __init__(self, board):
        self.board = board

    def compute_visibility(self, viewer_x, viewer_y):
        self.board.clear_visibility()
        for i in portals:
            self.compute_visibility2(viewer_x, viewer_y, viewer_x, viewer_y, *(i[0:4]))

        # POSTPROCESSING #
        temp = [row[:] for row in self.board.vis_map]  # gotta edit the temp, don't want to propagate this
        for y, row in enumerate(self.board.vis_map[:-1]):
            for x, elem in enumerate(row[:-1]):
                for wx, wy, cx, cy in ((0, 0, 1, 0), (1, 0, 1, 1), (1, 1, 0, 1), (0, 1, 0, 0)):
                    if (self.board.is_solid(x + wx, y + wy) and self.board.is_visible(x + wx, y + wy)
                            and self.board.is_solid(x + (not wx), y + (not wy)) and self.board.is_visible(x + (not wx), y + (not wy))
                            and not self.board.is_solid(x + cx, y + cy) and self.board.is_visible(x + cx, y + cy)
                            and self.board.is_solid(x + (not cx), y + (not cy))):
                        temp[y + (not cy)][x + (not cx)] = 2  # the literal corner case: all sides are visible but the corner cannot
        self.board.vis_map = temp


    def compute_visibility2(self, viewer_x, viewer_y, target_x, target_y, ldx, ldy, rdx, rdy):
        if (self.board.oob(target_x, target_y)):
            return

        self.board.set_visible(target_x, target_y)

        if (self.board.is_solid(target_x, target_y)):
            return

        dx = 2 * (target_x - viewer_x)
        dy = 2 * (target_y - viewer_y)

        for i in portals:
            pldx = dx + i[0]
            pldy = dy + i[1]
            prdx = dx + i[2]
            prdy = dy + i[3]

            if a_right_of_b(ldx, ldy, pldx, pldy):
                cldx = ldx
                cldy = ldy
            else:
                cldx = pldx
                cldy = pldy
            if a_right_of_b(rdx, rdy, prdx, prdy):
                crdx = prdx
                crdy = prdy
            else:
                crdx = rdx
                crdy = rdy

            if a_right_of_b(crdx, crdy, cldx, cldy):
                self.compute_visibility2(viewer_x, viewer_y, target_x + i[4], target_y + i[5], cldx, cldy, crdx, crdy)
