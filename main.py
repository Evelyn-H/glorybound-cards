import re
import strictyaml as yaml
from strictyaml import Map, MapPattern, EmptyDict, Str, Seq, Int, Any, Optional, CommaSeparated, Regex, load
import jinja2
import os
import glob
from jinja2 import Template


schema = Map({
    'path': Str(),
    'colors': Regex(r'[0-9a-fA-F]{6}\s*-\s*[0-9a-fA-F]{6}'),
    'cards': Seq(
        MapPattern(
            Str(), Map({
                'cost': Regex(r'[SWFAX]*'), 
                Optional('types'): CommaSeparated(Regex(r'oneshot|permanent|innate')),
                'text': Str(), 
                Optional('purchase'): Int(),
                Optional('upgrade cost'): Int(),
                Optional('upgrade'): Str(),

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
        self.types = [t.strip() for t in (d['types'] or [])]
        self.text = d['text']
        self.purchase = d['purchase']
        self.upgrade_cost = d['upgrade cost']
        self.upgrade = d['upgrade']

    def __str__(self):
        return f'<{self.name} {{{self.cost}}} [{self.purchase}]:\n  - ({", ".join(self.types)}) \n  - {repr(self.text)} \n  - [{self.upgrade_cost}: {repr(self.upgrade)}]>'


class Path(object):
    def __init__(self, name, colors, cards):
        self.name = name
        self.colors = colors
        self.cards = cards

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
        # print(*cards, sep='\n')
        return Path(name, colors, cards)



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

names = [
    'berserker',
    # 'fireheart',
    # 'legionnaire',
    # 'dancer',
    # 'arcanist',
    # 'assassin',
    # 'windwalker',
    # 'hammer-priest',
    # 'druid',
    # 'test',
]
# paths = [Path.from_file(f'paths/{n}.yaml') for n in names]

paths = [Path.from_file(f) for f in glob.glob('paths/*.yaml')]

print(template.render(
    paths=paths,
))
