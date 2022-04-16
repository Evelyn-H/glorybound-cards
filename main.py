import os
import sys
import glob
import re
import itertools
import strictyaml as yaml
from strictyaml import Map, MapPattern, EmptyDict, Str, Seq, Int, Bool, Any, Optional, CommaSeparated, Regex, load
import jinja2
from jinja2 import Template
import colormath
import colormath.color_objects
import colormath.color_diff
import colormath.color_conversions

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


schema = Map({
    'path': Str(),
    'colors': Regex(r'[0-9a-fA-F]{6}\s*-\s*[0-9a-fA-F]{6}'),
    Optional('extras'): Str(),
    Optional('passive name'): Str(),
    Optional('passive'): Str(),
    'cards': Seq(
        MapPattern(
            Str(), Map({
                'cost': Regex(r'[SWFAXH]*'), 
                Optional('types'): CommaSeparated(Regex(r'oneshot|permanent|innate|heirloom|support')),
                Optional('linked'): Str(),
                Optional('linked type'): Str(),
                Optional('linked short'): Bool(),
                Optional('path card name'): Str(),
                'text': Str(), 
                Optional('purchase'): Int(),
                Optional('upgrade cost'): Int(),
                Optional('upgrade'): Str(),
                Optional('big art'): Bool(),
                Optional('designer'): Str(),
            })
        )
    ),
    # "c": EmptyDict() | Seq(MapPattern(Str(), Str())),
})

class Card(object):
    def __init__(self, d):
        name, d = d.popitem()
        class MyDict(dict):
            def __missing__(self, key):
                return None
            def __getitem__(self, key):
                val = dict.__getitem__(self, key)
                if isinstance(val, str):
                    return val.strip().replace('\n', '\n\n')
                return val
        d = MyDict(d)
        self.name = name
        self.cost = d['cost']
        self.text = d['text']
        self.types = [t.strip() for t in (d['types'] or [])]
        if '\\sequence' in self.text:
            self.types.append('sequence')
        self.linked = d['linked']
        self.linked_type = d['linked type']
        self.linked_short = d['linked short']
        self.path_card_name = d['path card name'] or self.name
        self.linked_to = []
        self.purchase = d['purchase']
        self.upgrade_cost = d['upgrade cost']
        self.upgrade = d['upgrade']
        self.big_art = d['big art']
        self.designer = d['designer']

    def __str__(self):
        return f'<{self.name} {{{self.cost}}} [{self.purchase}]:\n  - ({", ".join(self.types)}) \n  - {repr(self.text)} \n  - [{self.upgrade_cost}: {repr(self.upgrade)}]>'


class Path(object):
    def __init__(self, name, colors, cards, extras=None, passive_name=None, passive=None):
        self.name = name
        self.colors = colors
        self.cards = cards
        self.extras = extras
        self.passive_name = passive_name
        self.passive = passive

    @classmethod
    def from_file(cls, filename):
        with open(filename, 'r') as file:
            text = file.read()

        def fix_string_stuff(text):
            text = text.split('\n')
            return '\n'.join([re.sub("^(\s+)([a-zA-Z ]+:)\s*$", lambda m: m.group(1) + m.group(2) + " >\n" + m.group(1)+"  ", line) for line in text])

        # print(text)
        # text = fix_string_stuff(text)
        # print(text)

        config = yaml.load(text, schema)
        data = config.data
        # data = yaml.load(text)
        # print(repr(data))

        name = data['path']
        colors = tuple([c.strip() for c in data['colors'].split('-')])
        cards = [Card(card) for card in data['cards']]
        extras = data.get('extras', None)
        passive_name = data.get('passive name', None)
        passive = data.get('passive', None)
        # print(*cards, sep='\n')
        path = Path(name, colors, cards, extras, passive_name, passive)
        path.build_links()
        return path

    def card_by_name(self, name):
        matches = [c for c in self.cards if c.name == name]
        if len(matches) > 0:
            return matches[0]
        else:
            return None

    def build_links(self):
        for c in self.cards:
            if c.linked:
                if '{' in c.linked:
                    linked_cards = re.findall(r"\{(.*?)\}", c.linked)
                else:
                    linked_cards = [c.linked]
                for l in linked_cards:
                    self.card_by_name(l).linked_to.append(c)


def check_colors(paths):
    new = colormath.color_objects.sRGBColor.new_from_rgb_hex
    def convert(c):
        target = colormath.color_objects.LabColor
        c = colormath.color_conversions.convert_color(c, colormath.color_objects.CMYKColor)
        return colormath.color_conversions.convert_color(c, target)

    comparisons = []
    for path_a, path_b in itertools.combinations(paths, 2):
        if path_a.name == path_b.name:
            continue
        
        a_left  = convert(new(path_a.colors[0]))
        a_right = convert(new(path_a.colors[1]))
        b_left  = convert(new(path_b.colors[0]))
        b_right = convert(new(path_b.colors[1]))

        # symmetric sides
        diff_l = colormath.color_diff.delta_e_cie2000(a_left, b_left)
        diff_r = colormath.color_diff.delta_e_cie2000(a_right, b_right)
        diff_l_s = colormath.color_diff.delta_e_cie2000(a_left, b_right)
        diff_r_s = colormath.color_diff.delta_e_cie2000(a_right, b_left)
        comparisons += [(path_a.name, path_b.name, diff_l, diff_r, False)]
        comparisons += [(path_a.name, path_b.name, diff_l_s, diff_r_s, True)]
        eprint(f"{path_a.name} - {path_b.name}: l={diff_l},  r={diff_r}")

    eprint('----\n')
    comparisons.sort(key=lambda c: c[2]**2+c[3]**2, reverse=True)
    eprint('\n'.join(map(str, comparisons)))

check_colors([Path.from_file(f) for f in glob.glob('paths/*.yaml')])
# input()
# quit()

latex_jinja_env = jinja2.Environment(
	block_start_string = '\BLOCK{',
	block_end_string = '}',
	variable_start_string = '\VAR{',
	variable_end_string = '}',
	comment_start_string = '\#{',
	comment_end_string = '}',
	line_statement_prefix = '%%',
	line_comment_prefix = '%#',
	trim_blocks = True,
    lstrip_blocks = True,
	autoescape = False,
	loader = jinja2.FileSystemLoader(os.path.abspath('.'))
)

template = latex_jinja_env.get_template('latex/glorybound_template.tex')

# print(sys.argv)
if sys.argv.count('-all') > 0:
    paths = [Path.from_file(f) for f in sorted(glob.glob('paths/*.yaml'))]
else:
    names = [
        # '_heirlooms',
        # 'arcanist',
        # 'archer',
        # 'assassin',
        # 'berserker',
        # 'bogwitch',
        # 'dancer',
        # 'druid',
        # 'fireheart',
        # 'guardian',
        # 'hammerpriest',
        # 'jester',
        # 'legionnaire',
        # 'lichknight',
        # 'mariner',
        # 'storyteller',
        # 'tinker',
        # 'traveler',
        # 'windwalker', 

        '_talents',
        'urchin',
        'farmhand',
        'apprentice',
        'disciple',
        'noble',
        'prodigy',
        'outlander',
        'soldier',
    ]
    paths = [Path.from_file(f'paths/{n}.yaml') for n in sorted(names)]

paths.sort(key=lambda p: p.name)

eprint([(len(p.cards), p.name) for p in paths])

eprint([[(c.name, c.linked_to) for c in path.cards if len(c.linked_to) > 0] for path in paths])

print(template.render(
    paths=paths,
))
