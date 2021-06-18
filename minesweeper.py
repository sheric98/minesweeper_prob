from sortedcontainers import SortedDict
import random

# generate combinations and complement
def comb_and_comp(lst, n):
    # no combinations
    if len(lst) < n or n < 0:
        return
    # trivial 'empty' combination
    if n == 0 or lst == []:
        yield [], lst
    else:
        first, rest = lst[0], lst[1:]
        # combinations that contain the first element
        for in_, out in comb_and_comp(rest, n - 1):
            yield [first] + in_, out
        # combinations that do not contain the first element
        for in_, out in comb_and_comp(rest, n):
            yield in_, [first] + out


class Tile:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.num = None
        self.neighs = set()

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other):
        return (self.x, self.y) == (other.x, other.y)

    def __repr__(self):
        return "Tile " + str((self.x, self.y)) + ": " + str(self.num)

    def add_neighs(self, neighs):
        for neigh in neighs:
            self.neighs.add(neigh)

    def set_num(self, num):
        self.num = num


class Chain:
    def __init__(self, num_mines):
        self.num_mines = num_mines
        self.mines = set()
        self.safe = set()

    def __hash__(self):
        return hash(id(self))

    def __eq__(self, other):
        return id(self) == id(other)

    def copy(self):
        ret = Chain(self.num_mines)
        ret.mines = self.mines.copy()
        ret.safe = self.safe.copy()
        return ret

    def update(self, new_mines, new_safes):
        self.mines.update(new_mines)
        self.safe.update(new_safes)

    def check_tile(self, tile):
        neigh_mines = 0

        hiddens = []
        for neigh in tile.neighs:
            if neigh in self.mines:
                neigh_mines += 1
            elif neigh not in self.safe and neigh.num is None:
                hiddens.append(neigh)

        mines_remain = tile.num - neigh_mines

        # too many mines in this chain
        if mines_remain + len(self.mines) > self.num_mines:
            return None, None, []
        
        combs = comb_and_comp(hiddens, mines_remain)

        upd_mines = None
        upd_safes = None
        new_chains = []
        for idx, (new_mines, new_safes) in enumerate(combs):
            if idx == 0:
                upd_mines = new_mines
                upd_safes = new_safes
            else:
                chain = self.copy()
                chain.update(new_mines, new_safes)
                new_chains.append(chain)

        if upd_mines is not None and upd_safes is not None:
            self.update(upd_mines, upd_safes)

        return upd_mines, upd_safes, new_chains

    def remove_safe_tile(self, tile):
        self.safe.remove(tile)


class ChainMap:
    def __init__(self, tiles, num_mines):
        self.num_tiles = sum(len(row) for row in tiles)
        self.num_mines = num_mines
        self.tot_mine_cnt = 0
        self.unused_tiles = set()
        self.chains = {Chain(num_mines)}
        self.mine_tiles = {}
        self.safe_tiles = {}
        self.updates = set()
        self.mine_chain_counts = {}
        self.prev_counts = {}
        self.sorted_counts = SortedDict()
        self.init_tiles_counts(tiles)


    def init_tiles_counts(self, tiles):
        for row in tiles:
            for tile in row:
                self.mine_tiles[tile] = set()
                self.safe_tiles[tile] = set()
                self.mine_chain_counts[tile] = 0
                self.unused_tiles.add(tile)

    def add_mine_tile_chain(self, tile, chain):
        self.mine_tiles[tile].add(chain)
        self.mine_chain_counts[tile] += 1
        if tile in self.mine_chain_counts:
            self.updates.add(tile)

    def add_safe_tile_chain(self, tile, chain):
        self.safe_tiles[tile].add(chain)
        if tile in self.mine_chain_counts:
            self.updates.add(tile)

    def remove_mine_tile_chain(self, tile, chain):
        self.mine_tiles[tile].remove(chain)
        self.mine_chain_counts[tile] -= 1
        if tile in self.mine_chain_counts:
            self.updates.add(tile)

    def remove_safe_tile_chain(self, tile, chain):
        self.safe_tiles[tile].remove(chain)

    def remove_chain(self, chain):
        self.chains.remove(chain)
        self.tot_mine_cnt -= len(chain.mines)
        for mine_tile in chain.mines:
            self.remove_mine_tile_chain(mine_tile, chain)
            
        for safe_tile in chain.safe:
            self.remove_safe_tile_chain(safe_tile, chain)

    def add_new_chain(self, chain):
        self.chains.add(chain)
        self.tot_mine_cnt += len(chain.mines)
        for mine_tile in chain.mines:
            self.add_mine_tile_chain(mine_tile, chain)
        for safe_tile in chain.safe:
            self.add_safe_tile_chain(safe_tile, chain)

    def update_chain(self, chain, upd_mines, upd_safes):
        self.tot_mine_cnt += len(upd_mines)
        for mine_tile in upd_mines:
            self.add_mine_tile_chain(mine_tile, chain)
        
        for safe_tile in upd_safes:
            self.add_safe_tile_chain(safe_tile, chain)

    def remove_count_tile(self, tile):
        if tile in self.prev_counts:
            prev_count = self.prev_counts[tile]
            self.sorted_counts[prev_count].remove(tile)
            if len(self.sorted_counts[prev_count]) == 0:
                del self.sorted_counts[prev_count]

    def used_tile(self, tile):
        if tile in self.unused_tiles:
            self.unused_tiles.remove(tile)

    def update_used_tiles(self, upd_mines, upd_safe):
        for tile in upd_mines:
            self.used_tile(tile)
        for tile in upd_safe:
            self.used_tile(tile)

    def update_tile(self, tile):
        self.used_tile(tile)

        remove_chains = self.mine_tiles[tile].copy()

        # update chains with tile we are removing
        for safe_chain in self.safe_tiles[tile]:
            safe_chain.remove_safe_tile(tile)

        # remove tile from chain counts and sorted counts
        del self.mine_chain_counts[tile]
        self.remove_count_tile(tile)
        if tile in self.updates:
            self.updates.remove(tile)

        tot_new_chains = []
        for chain in self.chains:
            upd_mines, upd_safes, new_chains = chain.check_tile(tile)

            # impossible chain
            if upd_mines is None or upd_safes is None:
                remove_chains.add(chain)
            
            else:
                self.update_used_tiles(upd_mines, upd_safes)
                self.update_chain(chain, upd_mines, upd_safes)
                tot_new_chains += new_chains

        # add new chains
        for new_chain in tot_new_chains:
            self.add_new_chain(new_chain)

        # remove safe tiles
        self.safe_tiles[tile].clear()

        # remove chains
        for remove in remove_chains:
            self.remove_chain(remove)

    def get_lowest_prob(self):
        if len(self.sorted_counts) == 0:
            return []
        
        mine_cnt, tiles = self.sorted_counts.peekitem(index=0)
        if mine_cnt == 0:
            return list(tiles)
        else:
            # calculate probability of random tile versus lowest
            if len(self.chains) == 0:
                used_mines = 0
            else:
                used_mines = self.tot_mine_cnt / len(self.chains)
            unused_mines = self.num_mines - used_mines

            # reveal all unused tiles if we know there are no mines
            if unused_mines == 0 and len(self.unused_tiles) > 0:
                return list(self.unused_tiles)

            if len(self.unused_tiles) == 0:
                unused_prob = 1
            else:
                unused_prob = unused_mines / len(self.unused_tiles)

            # no mines left
            if mine_cnt == len(self.chains) and unused_prob == 1:
                return []

            # lowest probability in the chain
            low_prob = mine_cnt / len(self.chains)

            # probability of lowest is smaller than a random choice
            if low_prob <= unused_prob:                
                return [random.choice(list(tiles))]
            # random choice is less likely
            else:
                return [random.choice(list(self.unused_tiles))]

    def update_tiles(self, tiles):
        for tile in tiles:
            self.update_tile(tile)

        # update the ordered dict
        for tile in self.updates:
            # remove previous count
            self.remove_count_tile(tile)

            count = self.mine_chain_counts[tile]

            # add new count
            if count not in self.sorted_counts:
                self.sorted_counts[count] = set()
            self.sorted_counts[count].add(tile)

            self.prev_counts[tile] = count
        
        self.updates.clear()

        return self.get_lowest_prob()


NEIGHS = [
    (-1, 1), (0, 1), (1, 1),
    (-1, 0), (1, 0),
    (-1, -1), (0, -1), (1, -1)
]

class Board:
    def __init__(self, width, height, num_mines):
        self.width = width
        self.height = height
        self.num_mines = num_mines
        self.tiles = self.gen_tiles()
        self.chainMap = ChainMap(self.tiles, num_mines)

    def in_board(self, x, y):
        return x >= 0 and x < self.width and \
            y >= 0 and y < self.height
    
    def get_neighs(self, x, y):
        ret = []
        for neigh in NEIGHS:
            new_x = x + neigh[0]
            new_y = y + neigh[1]
            if self.in_board(new_x, new_y):
                ret.append((new_x, new_y))
        return ret

    def gen_tiles(self):
        tiles = [[None] * self.width for _ in range(self.height)]

        # create tile objects
        for x in range(self.width):
            for y in range(self.height):
                tiles[y][x] = Tile(x, y)
        
        # add Neighbors
        for x in range(self.width):
            for y in range(self.height):
                neighs = self.get_neighs(x, y)
                neigh_tiles = [tiles[j][i] for (i, j) in neighs]
                tiles[y][x].add_neighs(neigh_tiles)

        return tiles

    # pairs of form list of ([(x, y), number])
    def reveal_tiles(self, pairs):
        tiles = []
        for (x, y), num in pairs:
            tile = self.tiles[y][x]
            tile.set_num(num)
            tiles.append(tile)

        next_reveals = self.chainMap.update_tiles(tiles)
        return next_reveals
