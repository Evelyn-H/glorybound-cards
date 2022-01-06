import os
import sys
import glob
import re
import strictyaml as yaml
from strictyaml import Map, MapPattern, EmptyDict, Str, Seq, Int, Bool, Any, Optional, CommaSeparated, Regex, load
import jinja2
from jinja2 import Template

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


schema = Map({
    'path': Str(),
    'colors': Regex(r'[0-9a-fA-F]{6}\s*-\s*[0-9a-fA-F]{6}'),
    'resources': Regex(r'[WSF]{3}'),
    Optional('extras'): Str(),
    'cards': Seq(
        MapPattern(
            Str(), Map({
                'cost': Regex(r'[SWFAX]*'), 
                Optional('types'): CommaSeparated(Regex(r'oneshot|permanent|innate')),
                Optional('linked'): Str(),
                Optional('linked type'): Str(),
                Optional('path card name'): Str(),
                'text': Str(), 
                Optional('purchase'): Int(),
                Optional('upgrade cost'): Int(),
                Optional('upgrade'): Str(),
                Optional('big art'): Bool(),
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
        self.path_card_name = d['path card name'] or self.name
        self.linked_to = []
        self.purchase = d['purchase']
        self.upgrade_cost = d['upgrade cost']
        self.upgrade = d['upgrade']
        self.big_art = d['big art']

    def __str__(self):
        return f'<{self.name} {{{self.cost}}} [{self.purchase}]:\n  - ({", ".join(self.types)}) \n  - {repr(self.text)} \n  - [{self.upgrade_cost}: {repr(self.upgrade)}]>'


class Path(object):
    def __init__(self, name, colors, resources, cards, extras=None):
        self.name = name
        self.colors = colors
        self.resources = resources
        self.cards = cards
        self.extras = extras

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
        resources = data['resources']
        cards = [Card(card) for card in data['cards']]
        extras = data.get('extras', None)
        # print(*cards, sep='\n')
        path = Path(name, colors, resources, cards, extras)
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
    paths = [Path.from_file(f) for f in glob.glob('paths/*.yaml')]
else:
    names = [
        # 'berserker',
        # 'fireheart',
        # 'legionnaire',
        # 'dancer',
        # 'arcanist',
        # 'assassin',
        # 'windwalker',
        # 'hammerpriest',
        # 'druid',
        # 'mariner',
        # 'guardian',
        # 'jester',
        # 'traveler',
        # 'bogwitch',
        # 'lichknight',
        # 'tinker',
        'storyteller',
        # 'test',
    ]
    paths = [Path.from_file(f'paths/{n}.yaml') for n in names]

eprint([(len(p.cards), p.name) for p in paths])

eprint([[(c.name, c.linked_to) for c in path.cards if len(c.linked_to) > 0] for path in paths])

print(template.render(
    paths=paths,
))
