import unittest

import math

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from minesweeper import Chain, ChainMap, Board


def gen_tiles(width, height, num_mines, reveals):
    ret = Board(width, height, num_mines).tiles
    for (x, y), num in reveals:
        ret[y][x].set_num(num)
    return ret

def update_tiles(tiles, reveals):
    for (x, y), num in reveals:
        tiles[y][x].set_num(num)

def get_tiles(tiles, reveals):
    return [tiles[y][x] for (x, y), _ in reveals]

test_reveals_simple = [
    ((0, 0), 3),
]

test_reveals = [
    ((1, 1), 2),
    ((2, 1), 1),
    ((3, 1), 1),
    ((1, 2), 1),
    ((2, 2), 0),
    ((3, 2), 1),
    ((1, 3), 3),
    ((2, 3), 1),
    ((3, 3), 2),
]

next_reveals = [
    ((0, 1), 2),
    ((3, 4), 1),
]

test_too_many = [
    ((1, 0), 1),
    ((2, 0), 1),
]

test_unused = [
    ((1, 1), 1)
]

class ChainTests(unittest.TestCase):

    def test_check_tile_simple(self):
        revealed_two_by_two = gen_tiles(2, 2, 3, test_reveals_simple)
        chain = Chain(3)
        revealed_check = test_reveals_simple[0]
        (x, y), _ = revealed_check
        tile = revealed_two_by_two[y][x]

        upd_mines, upd_safe, next_chains = chain.check_tile(tile)
        expected_mines = [
            (1, 0),
            (0, 1),
            (1, 1)
        ]
        expected_mine_tiles = set([revealed_two_by_two[j][i]
            for (i, j) in expected_mines])

        # check that expected mines and safe are correct
        self.assertEqual(expected_mine_tiles, set(upd_mines))
        self.assertEqual(expected_mine_tiles, chain.mines)
        self.assertEqual(len(upd_safe), 0)
        self.assertEqual(set(upd_safe), chain.safe)

        # should be only one possibility in this situation
        self.assertEqual(len(next_chains), 0)

    def test_check_tile(self):
        revealed_five_by_five = gen_tiles(5, 5, 10, test_reveals)
        chain = Chain(10)
        revealed_check = test_reveals[0]
        (x, y), num = revealed_check
        tile = revealed_five_by_five[y][x]
        neighs = set([t for t in tile.neighs if t.num is None])
        num_neighs = len(neighs)

        upd_mines, upd_safe, next_chains = chain.check_tile(tile)

        self.assertEqual(len(upd_mines), num)
        self.assertEqual(len(upd_safe), num_neighs - num)
        self.assertEqual(set(upd_mines), chain.mines)
        self.assertEqual(set(upd_safe), chain.safe)

        combinations = math.comb(num_neighs, num)

        # -1 because first one is the original chain
        self.assertEqual(len(next_chains), combinations - 1)
        for next in next_chains:
            # check chains have correct number of mines and safes
            self.assertEqual(len(next.mines), num)
            self.assertEqual(len(next.safe), num_neighs - num)

            # check that mines and safes are not equal to current chain
            self.assertNotEqual(chain.mines, next.mines)
            self.assertNotEqual(chain.safe, next.safe)

        # check pairs are not equal
        for idx, next1 in enumerate(next_chains):
            for next2 in next_chains[idx+1:]:
                self.assertNotEqual(next1.mines, next2.mines)
                self.assertNotEqual(next1.safe, next2.safe)

        # try a second tile
        all_chains = [chain] + next_chains
        check1 = test_reveals[1]
        (x1, y1), num1 = check1
        tile1 = revealed_five_by_five[y1][x1]
        neighs1 = set([t for t in tile1.neighs if t.num is None
            and t not in neighs])
        all_neighs1 = set([t for t in tile1.neighs if t.num is None])
        num_neighs1 = len(neighs1)
        tot_neighs = num_neighs1 + num_neighs

        # chains_twice is all chains after second update
        # valid_updates is the number of chains from the first try
        # that weren't impossible.
        chains_twice = []
        valid_updates = 0
        for c in all_chains:
            upd_mines, upd_safe, next_chains = c.check_tile(tile1)
            if upd_mines is not None and upd_safe is not None:
                chains_twice += next_chains
                chains_twice.append(c)
                valid_updates += 1

        # there should have been one original chain that is impossible
        self.assertEqual(valid_updates, len(all_chains) - 1)

        # new combinations
        new_combinations = math.comb(num_neighs1, num1) * valid_updates
        self.assertEqual(len(chains_twice), new_combinations)
        
        # check number of mines
        for c in chains_twice:
            adj_mines = len([t for t in c.mines if t in neighs])
            adj_mines1 = len([t for t in c.mines if t in all_neighs1])

            self.assertEqual(adj_mines, num)
            self.assertEqual(adj_mines1, num1)
            self.assertEqual(len(c.safe), tot_neighs - len(c.mines))

        for idx, c1 in enumerate(chains_twice):
            for c2 in chains_twice[idx+1:]:
                self.assertNotEqual(c1.mines, c2.mines)
                self.assertNotEqual(c1.safe, c2.safe)

        
    def test_check_impossible(self):
        revealed_five_by_five = gen_tiles(5, 5, 10, test_reveals)
        chain = Chain(10)
        mines = [
            (1, 0),
            (2, 0),
        ]
        safes = [
            (0, 0),
            (0, 1),
            (0, 2),
        ]
        mine_tiles = [revealed_five_by_five[m[1]][m[0]] for m in mines]
        safe_tiles = [revealed_five_by_five[s[1]][s[0]] for s in safes]
        chain.update(mine_tiles, safe_tiles)

        # there are 2 mines next to the one, so should produce a contradiction
        contradiction = test_reveals[1]
        (x, y), _ = contradiction
        tile = revealed_five_by_five[y][x]

        # should be none since impossible
        upd_mines, upd_safe, _ = chain.check_tile(tile)

        self.assertIsNone(upd_mines)
        self.assertIsNone(upd_safe)

    def test_check_too_many(self):
        num_mines = 1
        revealed_too_many = gen_tiles(4, 2, num_mines, test_too_many)
        chain = Chain(num_mines)
        tiles = get_tiles(revealed_too_many, test_too_many)

        # first tile. Should have 4 chains total
        upd_mines, upd_tiles, next_chains = chain.check_tile(tiles[0])
        self.assertIsNotNone(upd_mines)
        self.assertIsNotNone(upd_tiles)
        all_chains = [chain] + next_chains
        self.assertEqual(len(all_chains), 4)

        # now check second tile. Should only have 2 possibilities remaining
        tot_final_chains = []
        for c in all_chains:
            upd_m, upd_s, next_cs = c.check_tile(tiles[1])
            if upd_m is not None and upd_s is not None:
                tot_final_chains.append(c)
                tot_final_chains.extend(next_cs)

        self.assertEqual(len(tot_final_chains), 2)

        
class ChainMapTests(unittest.TestCase):

    def test_simple_update_single(self):
        revealed_two_by_two = gen_tiles(2, 2, 3, test_reveals_simple)
        chainMap = ChainMap(revealed_two_by_two, 3)
        revealed_check = test_reveals_simple[0]
        (x, y), _ = revealed_check
        tile = revealed_two_by_two[y][x]
        all_tiles = []
        for row in revealed_two_by_two:
            for t in row:
                all_tiles.append(t)

        chainMap.update_tile(tile)

        # check attributes.
        # should still have one chain
        self.assertEqual(len(chainMap.chains), 1)
        
        # all tiles except our "tile" should have 1 mine.
        for t in all_tiles:
            if t != tile:
                self.assertEqual(len(chainMap.mine_tiles[t]), 1)
                self.assertEqual(chainMap.chains, chainMap.mine_tiles[t])
                self.assertEqual(chainMap.mine_chain_counts[t], 1)
                self.assertEqual(len(chainMap.safe_tiles[t]), 0)
            else:
                self.assertEqual(len(chainMap.mine_tiles[t]), 0)
                with self.assertRaises(KeyError):
                    chainMap.mine_chain_counts[t]
        
        # expect all except the "tile" to be updated
        expected_updates = set(all_tiles)
        expected_updates.remove(tile)
        self.assertEqual(chainMap.updates, expected_updates)

    def test_simple_full(self):
        revealed_two_by_two = gen_tiles(2, 2, 3, test_reveals_simple)
        chainMap = ChainMap(revealed_two_by_two, 3)
        self.assertEqual(len(chainMap.unused_tiles), 4)
        tiles = get_tiles(revealed_two_by_two, test_reveals_simple)

        update = chainMap.update_tiles(tiles)
        # no updates to be made
        self.assertEqual(len(update), 0)

        # make sure that our counts are correct
        for t, cnt in chainMap.mine_chain_counts.items():
            self.assertIn(t, chainMap.sorted_counts[cnt])

        for cnt, ts in chainMap.sorted_counts.items():
            for t in ts:
                self.assertEqual(chainMap.mine_chain_counts[t], cnt)

        # no unused tiles left
        self.assertEqual(len(chainMap.unused_tiles), 0)

    def test_fives_full(self):
        revealed_five_by_five = gen_tiles(5, 5, 10, test_reveals)
        chainMap = ChainMap(revealed_five_by_five, 10)
        tiles = get_tiles(revealed_five_by_five, test_reveals)
        update = chainMap.update_tiles(tiles)
        
        # check properties of the chainmap. 16 Calculated manually
        tot_chains = 16
        self.assertEqual(len(chainMap.chains), tot_chains)

        # keys are number of mines, items are sets of coords
        # these are also calculated manually
        expected_tuple_counts = {
            0: {(0, 1), (3, 4)},
            2: {(3, 0), (4, 1)},
            4: {(2, 0), (4, 0), (4, 2)},
            7: {(0, 3), (1, 4)},
            9: {(0, 0), (0, 2), (2, 4), (4, 4)},
            10: {(1, 0), (4, 3)},
            16: {(0, 4)},
        }

        expected_mine_counts = {}
        for key, val in expected_tuple_counts.items():
            expected_mine_counts[key] = set()
            for x, y in val:
                expected_mine_counts[key].add(revealed_five_by_five[y][x])
            
        actual_mine_counts = {}
        for key, val in chainMap.sorted_counts.items():
            actual_mine_counts[key] = val

        self.assertEqual(actual_mine_counts, expected_mine_counts)

        # update tiles should just be tile with mine count of 0
        self.assertEqual(expected_mine_counts[0], set(update))

        # now we try a next update
        update_tiles(revealed_five_by_five, next_reveals)
        next_tiles = get_tiles(revealed_five_by_five, next_reveals)
        
        next_upd = chainMap.update_tiles(next_tiles)

        # manually calculated. Should only have 4 left
        next_tot_chains = 4
        self.assertEqual(len(chainMap.chains), next_tot_chains)

        expected_next_tup_cnts = {
            0: {(2, 0), (3, 0), (4, 0), (4, 1), (4, 3)},
            2: {(0, 0), (0, 2), (0, 3), (1, 4), (2, 4), (4, 4)},
            4: {(1, 0), (4, 2), (0, 4)},
        }

        expected_next_mine_cnts = {}
        for key, val in expected_next_tup_cnts.items():
            expected_next_mine_cnts[key] = set()
            for x, y in val:
                expected_next_mine_cnts[key].add(revealed_five_by_five[y][x])

        actual_next_mine_cnts = {}
        for key, val in chainMap.sorted_counts.items():
            actual_next_mine_cnts[key] = val

        self.assertEqual(actual_next_mine_cnts, expected_next_mine_cnts)

        # update tiles should just be tile with mine count of 0
        self.assertEqual(expected_next_mine_cnts[0], set(next_upd))

    def test_unused_tiles(self):
        revealed_six_by_six = gen_tiles(6, 6, 10, test_reveals)
        chainMap = ChainMap(revealed_six_by_six, 10)
        tiles = get_tiles(revealed_six_by_six, test_reveals)

        self.assertEqual(len(chainMap.unused_tiles), 36)
        _ = chainMap.update_tiles(tiles)

        # 25 of the tiles are accounted for
        self.assertEqual(len(chainMap.unused_tiles), 11)

        # now we try a next update
        update_tiles(revealed_six_by_six, next_reveals)
        next_tiles = get_tiles(revealed_six_by_six, next_reveals)
        
        _ = chainMap.update_tiles(next_tiles)

        # 3 more tiles accounted for
        self.assertEqual(len(chainMap.unused_tiles), 8)

    def test_check_too_many(self):
        num_mines = 1
        revealed_too_many = gen_tiles(4, 2, num_mines, test_too_many)
        chainMap = ChainMap(revealed_too_many, num_mines)
        tiles = get_tiles(revealed_too_many, test_too_many)

        upds = chainMap.update_tiles(tiles)

        self.assertEqual(set(upds), chainMap.sorted_counts[0])

    # check that a random unused tile is returned.
    def test_check_unused(self):
        num_mines = 2
        revealed = gen_tiles(5, 5, num_mines, test_unused)
        chainMap = ChainMap(revealed, num_mines)
        tiles = get_tiles(revealed, test_unused)
        
        upd = chainMap.update_tiles(tiles)
        self.assertEqual(len(upd), 1)
        self.assertIn(upd[0], chainMap.unused_tiles)
    
    # in this case, we are checking that all unused tiles are returned
    # since there are no mines in them.
    def test_check_unused_all(self):
        num_mines = 1
        revealed = gen_tiles(5, 5, num_mines, test_unused)
        chainMap = ChainMap(revealed, num_mines)
        tiles = get_tiles(revealed, test_unused)
        
        upd = chainMap.update_tiles(tiles)
        # 25 - 9 = 16 (unused tiles)
        self.assertEqual(len(upd), 16)
        self.assertEqual(set(upd), chainMap.unused_tiles)

    # in this case, we should get a tile with the nonzero prob, but
    # also not an unused tile.
    def test_non_zero_low(self):
        num_mines = 2
        revealed = gen_tiles(3, 4, num_mines, test_unused)
        chainMap = ChainMap(revealed, num_mines)
        tiles = get_tiles(revealed, test_unused)

        upd = chainMap.update_tiles(tiles)
        self.assertEqual(len(upd), 1)
        self.assertNotIn(upd[0], chainMap.unused_tiles)
        self.assertEqual(chainMap.prev_counts[upd[0]] / len(chainMap.chains),
            1 / 8)


class BoardTests(unittest.TestCase):

    def test_simple(self):
        board = Board(2, 2, 3)
        updates = board.reveal_tiles(test_reveals_simple)
        self.assertEqual(len(updates), 0)

    def test_five_by_five(self):
        board = Board(5, 5, 10)
        updates = board.reveal_tiles(test_reveals)
        self.assertEqual(len(updates), 2)
        self.assertEqual(set(updates), board.chainMap.sorted_counts[0])

if __name__ == '__main__':
    unittest.main()
