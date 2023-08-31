import os
import sys
import glob
import re
import itertools
import subprocess
import datetime
import math
from typing import List, Tuple
import strictyaml as yaml
from strictyaml import Map, MapPattern, EmptyDict, Str, Seq, Int, Bool, Any, Optional, CommaSeparated, Regex, load
import jinja2 as j2
from jinja2 import Template

from macros import macros

# ==== helpers ====

class MyDict(dict):
    def __missing__(self, key):
        return None

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        if isinstance(val, str):
            return val.strip().strip('\n').replace('\n', '\n\n')
        return val

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def flatten(l):
    return [item for sublist in l for item in sublist]

def cleanup(p: str):
    return p.replace(' ', '_').replace('\'', '_').replace(':', '_').replace(',', '_')


# ==== card definition schema ====

schema = Map({
    'kind': Str(),
    Optional('subname'): Str(),
    # Optional('colors'): Regex(r'[0-9a-fA-F]{6}\s*-\s*[0-9a-fA-F]{6}'),
    Optional('extras'): Str(),
    Optional('count'): Int(),

    'cards': Seq(
        MapPattern(
            Str(), Map({
                Optional('cost'): Int(), 
                'text': Str(), 
                Optional('art'): Str(), 
                Optional('types'): Regex(r'\s*((move|starter|advanced|ascension|inspiration|ruined|permanent|item|augment|conjured|sequence|signature|mentor|rules)\s*)*'),

                Optional('invoke'): Str(), 
                Optional('invoketext'): Str(), 
                Optional('mentormove'): Str(),
                Optional('count'): Int(),
            })
        )
    ),
})



# ==== card & group objects ====

class Card(object):
    def __init__(self, d):
        name, d = d.popitem()
        d = MyDict(d)

        self._name = name
        self.cost = d['cost'] or 0
        self.text = d['text']
        self.types = [t.strip() for t in (d['types'].split(' ') or [])]
        # if '\\sequence' in self.text:
            # self.types.append('sequence')
        if self.landscape:
            self.types.append('landscape')
        self.invoke_name = d['invoke']
        self.invoke_text = d['invoketext']
        self.mentor_move = d['mentormove']
        self.mentor_move_card = None
        self.parent_mentor = None
        self._art = d['art']
        self._count = d['count']

    @property
    def art_filename(self):
        base = self._art or self.name_clean
        return f'../../assets/art/cards/{base}.png'
        # return f'../../assets/invalid'

    @property
    def name(self):
        if 'signature' in self.types:
            return 'Signature: ' + self._name
        else:
            return self._name

    @property
    def name_clean(self):
        return cleanup(self.name)

    @property
    def name_short(self):
        if ',' in self.name:
            return self.name.split(',')[0]
        else:
            return self.name.split(' ')[0]

    @property
    def type_line(self):
        def maybe_add(type):
            if type in self.types:
                return (type.title() + ' ')
            else:
                return ''

        line = ''
        line += maybe_add('conjured')
        line += maybe_add('starter')
        line += maybe_add('advanced')
        line += maybe_add('signature')
        line += maybe_add('mentor')

        line += maybe_add('move')
        line += maybe_add('item')
        line += maybe_add('augment')
        line += maybe_add('inspiration')

        if self.is_mentor_move:
            line += f'({self.parent_mentor.name_short}) '

        subtypes = ''
        # subtypes += maybe_add('ruined')
        subtypes += maybe_add('ascension')
        subtypes += maybe_add('sequence')
        subtypes += maybe_add('permanent')

        if len(subtypes) > 0:
            line += f'- {subtypes}' 

        return line.strip()

    @property 
    def full_text(self):
        return self._full_text()

    @property 
    def full_text_mini(self):
        return self._full_text(mini=True)

    def _full_text(self, mini=False):
        text = ''
        text += '\\conjured\n\n' if 'conjured' in self.types and not 'augment' in self.types else ''
        text += '\\augment\n\n' if 'augment' in self.types else ''

        text += f'\\mentormove[{self.parent_mentor.name_short}]\n\n' if self.is_mentor_move and not mini else ''

        # text += '\\signature\n\n' if 'signature' in self.types else ''
        text += '\\ruined\n\n' if 'ruined' in self.types else ''

        text += '\\item\n\n' if 'item' in self.types else ''

        

        text += self.text

        text += '\n\n\\permanent' if 'permanent' in self.types else ''

        if self.invoke_name:
            # print((self.invoke_name, self.invoke_text))
            text += f'\n\n\\invoke_ability[{self.invoke_name}][{self.invoke_text.strip()}]'

        return text.strip() 

    @property
    def rendered_text(self):
        return self._rendered_text()

    @property
    def rendered_text_mini(self):
        return self._rendered_text(mini=True)

    def _rendered_text(self, mini=False):
        expanded, remainder = expand(self._full_text(mini))
        if len(remainder) > 0:
            raise Exception(f'unexpected text: {remainder}')

        expanded = expanded.strip()
        # print('---', expanded)
        html = '<div class="p">' + str.join('</div><div class="p">', filter(None, split_on_empty_lines(expanded))) + '</div>'
        # print(split_on_empty_lines(expanded))
        # print(html)

        if self.is_mentor:
            html += f'\n\n{render_mini_card(self.mentor_move_card)}\n\n'

        return html


    @property
    def ruined(self):
        return 'ruined' in self.types

    @property
    def conjured(self):
        return 'conjured' in self.types
        

    @property
    def inspiration(self):
        return 'inspiration' in self.types

    @property
    def inspiration_art(self):
        return f'../../assets/art/inspiration/{self.group.name_clean}.png'

    @property
    def is_mentor(self):
        return 'mentor' in self.types and not ('move' in self.types or 'item' in self.types)

    @property
    def is_mentor_move(self):
        return 'mentor' in self.types and ('move' in self.types or 'item' in self.types)

    @property
    def landscape(self):
        return self.is_mentor

    @property
    def symbols(self):
        symbols = []

        if self.group.kind == 'Archetype':
            symbols.append(('archetype', self.group.subname))

        if 'starter' in self.types:
            symbols.append(('starter', 'starter'))

        return symbols

    @property
    def sorting_icons(self):
        # symbols = [('kind', cleanup(self.group.kind))]
        # if self.group.kind == 'Archetype':
        #     symbols.append(('archetype', self.group.name_clean))

        symbols = [('kind', self.group.name_clean)]

        return symbols

    @property
    def count(self):
        return self._count or self.group.count or 1


class Group(object):
    def __init__(self, kind, cards, subname=None, extras=None, count=1):
        self.kind = kind
        self.subname = subname
        self.cards = cards
        self.extras = extras
        self.count = count

        # put a reference to the group in the cards
        for card in self.cards:
            card.group = self

    @property
    def name(self):
        if self.subname:
            return f"{self.kind}: {self.subname}"
        else:
            return self.kind

    @property
    def name_clean(self):
        return cleanup(self.name)

    @staticmethod
    def from_string(text):
        # eprint(text)
        config = yaml.load(text, schema)
        data = config.data
        # data = yaml.load(text)
        # print(repr(data))

        data = MyDict(data)

        kind = data['kind']
        subname = data['subname']
        # colors = tuple([c.strip() for c in data.get('colors', '000000 - 000000').split('-')])
        cards = [Card(card) for card in data['cards']]
        extras = data.get('extras', None)
        count = data.get('count', None)

        # link mentor move cards
        for card in cards:
            if card.mentor_move:
                try:
                    card.mentor_move_card = next(c for c in cards if c.name == card.mentor_move)
                    card.mentor_move_card.parent_mentor = card
                except StopIteration:
                    raise Exception(f"couldn't find mentor move: {card.mentor_move} for {card.name}")

        # print(*cards, sep='\n')
        return Group(kind, cards, subname, extras, count)

    @staticmethod
    def from_file(filename):
        with open(filename, 'r') as file:
            text = file.read()
            return Group.from_string(text)



# ==== macro expansion ====

# okay, writing a little parser combinator library based on regexes and overloading `or` and such would be really fun

def apply_macro(name: str, arguments: List[str]) -> str:
    # return f'[{name}: {arguments}]'
    func = macros.get(name)
    if not func:
        raise Exception(f"couldn't find macro: {name}")

    # print((name, arguments))
    return str(func(*arguments))

def read_block(text: str) -> Tuple[str, str]:
    match = re.match(r'\s*\[', text)
    if not match:
        return None

    expanded, remainder = expand(text[match.end():])
    if not remainder.startswith(']'):
        raise Exception('gotta end your block with a \']\'.')

    return expanded, remainder[1:]

def expand_once(text: str) -> Tuple[str, str]:
    # macros start with a '\' followed by a name and optionally arguments between [ and ]
    pattern_macro = r'(\\(?P<macro>(\w|_)+))'

    # regular text can't contain '\' or '[' or ']'
    pattern_text = r'[^\\\[\]]*'
    
    # match as much non-macro text as possible
    padding_match = re.match(pattern_text, text)
    consumed = text[: padding_match.end()]
    remainder = text[padding_match.end() :]
    # print((consumed, remainder))

    # if we have no text left it means there's no macro in this text, so just return it unaltered
    if len(remainder) == 0:
        return (consumed, '')

    if remainder.startswith(']'):
        return consumed, remainder

    # parse the macro
    match = re.match(pattern_macro, remainder)
    if not match:
        raise Exception(f'invalid macro call, error at: {remainder}')

    macro_name = match.group('macro')
    # print(match)
    remainder = remainder[match.end() :]

    # parse a variable number of arguments
    arguments = []
    while (block := read_block(remainder)) is not None:
        contents, remainder = block
        contents = insert_paragraphs(contents)
        arguments.append(contents.strip())

    # run the macro code on the arguments
    expanded = apply_macro(macro_name, arguments)

    # finally, return the expanded text, and what's left to parse
    # print((text, consumed, expanded, remainder))
    return consumed + expanded, remainder
    

def expand(text: str) -> Tuple[str, str]:
    expanded = ''
    remainder = text
    while remainder and not remainder.startswith(']'):
        consumed, remainder = expand_once(remainder)
        expanded += consumed
        # print((expanded, remainder))

    return expanded, remainder


# ==== textbox rendering ====

# https://stackoverflow.com/a/57097762
def split_on_empty_lines(s):
    # greedily match 2 or more new-lines
    blank_line_regex = r"(?:\r?\n *){2,}"
    return re.split(blank_line_regex, s.strip())

def insert_paragraphs(text):
    text = text.strip()
    split = list(filter(None, split_on_empty_lines(text)))
    if len(split) > 1:
        return '<div class="p">' + str.join('</div><div class="p">', split) + '</div>'
    return text


# ==== card rendering ====

card_jinja_env = j2.Environment(
	autoescape = True,
	loader = j2.FileSystemLoader(os.path.abspath('./templates'))
)

files = glob.glob('cards/**.yaml')
groups = [Group.from_file(f) for f in files]

date = datetime.date.today().strftime('%m/%d/%y')

def render_and_save_html(template_name, out_path, filename, **template_vars):
    template = card_jinja_env.get_template(template_name)
    try:
        out = template.render(**template_vars)
    except Exception as e:
        raise Exception(f'error while rendering [{filename}]: {e}')

    dir = "./" + cleanup(out_path) + '/'
    os.makedirs(dir, exist_ok=True) 
    with open(dir + cleanup(filename), 'w') as file:
        file.write(out)

def render_mini_card(card) -> str:
    template = card_jinja_env.get_template('mini_card.html')
    return template.render(card=card)



import asyncio
import queue


q = queue.Queue()
for i in range(24):
    q.put(i)

# https://www.delftstack.com/howto/python/parallel-for-loops-python/#use-the-asyncio-module-to-parallelize-the-for-loop-in-python
tasks = []
def background(f):
    def wrapped(*args, **kwargs):
        task = asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)
        tasks.append(task)
        return task
    return wrapped

@background
def render_image(html_file, out_file, resolution_x, resolution_y):
    # subprocess.run(f"firefox --no-remote -P glorybound --screenshot '{out_file}' --window-size={resolution_x},{resolution_y} file://'{html_file}'", shell=True)

    # the shenanigans with the profile folders here is to ensure we can run things in parallel
    # since firefox doesn't let you run multiple instances of the same profile
    # then the queue stuff is so we can limit the max number of profiles / instances so we don't blow up my computer
    profile_num = q.get()
    profile_path = f'./.profiles/prof{profile_num}'
    os.makedirs(profile_path, exist_ok=True) 
    command = f"firefox --no-remote --profile {profile_path} --screenshot '{out_file}' --window-size={resolution_x},{resolution_y} file://'{html_file}'"
    # print(command)
    subprocess.run(command, shell=True)
    q.put(profile_num)

@background
def make_pdf(group):
    os.makedirs('./build/pdfs/', exist_ok=True) 
    # subprocess.run(f"convert ./build/images/{cleanup(group.name)}/*.png ./build/pdfs/{cleanup(group.name)}.pdf", shell=True)
    cards = [f'./build/images/{cleanup(group.name)}/{cleanup(card.name)}.png' for card in group.cards]
    subprocess.run(f"convert {' '.join(cards)} ./build/pdfs/{cleanup(group.name)}.pdf", shell=True)

@background
def add_bleed(group, card):
    card_name = cleanup(card.name)+ f'[face,{card.count}]'
    os.makedirs(f'./build/print/{cleanup(group.name)}/', exist_ok=True) 
    # if card.landscape:
    #     # subprocess.run(f"convert ./build/images/{cleanup(group.name)}/{cleanup(card.name)}.png -resize 50% -gravity center -extent 1125x825 ./assets/bleed-overlay-landscape.png -composite ./build/print/{cleanup(group.name)}/{card_name}.png", shell=True)
    #     subprocess.run(f"convert ./build/images/{cleanup(group.name)}/{cleanup(card.name)}.png -rotate 90 -resize 50% -gravity center -extent 825x1125 ./assets/bleed-overlay.png -composite ./build/print/{cleanup(group.name)}/{card_name}.png", shell=True)
    # else:
    subprocess.run(f"convert ./build/images/{cleanup(group.name)}/{cleanup(card.name)}.png -resize 50% -gravity center -extent 825x1125 ./assets/bleed-overlay.png -composite ./build/print/{cleanup(group.name)}/{card_name}.png", shell=True)


# ==== main ====

if __name__ == '__main__':

    errors = []
    # render individual cards
    for group in groups:
        for card in group.cards:
            try:
                render_and_save_html(
                    'card.html', 'build/cards', f"{card.name}.html", 
                    card=card, group=group, date=date
                )
            except Exception as e:
                errors.append(e)
    
    if errors:
        print(*errors, sep='\n')
        exit()

    # render the whole groups
    for group in groups:
        render_and_save_html(
            'group.html', 'build/groups', f"{group.name}.html", 
            group=group, date=date
        )

    if sys.argv.count('--render') > 0:
        dpi = 600
        width, height = 63, 88 # in mm
        resolution_x = int(math.ceil(width / 25.4 * dpi)) # 1489 @ 600dpi
        resolution_y = int(math.ceil(height / 25.4 * dpi)) # 2079 @ 600dpi

        for group in groups:
            for card in group.cards:
                card_name = cleanup(card.name)
                html_file = os.path.abspath(f'./build/cards/{card_name}.html')
                # card_name = cleanup(card.name) + f'[face,{card.count}]'
                out_file = os.path.abspath(f'./build/images/{cleanup(group.name)}/{card_name}.png')
                # print(out_file)
                # print(html_file)
                if card.landscape:
                    x, y = resolution_y, resolution_x
                else:
                    x, y = resolution_x, resolution_y
                render_image(html_file, out_file, x, y)
        
        # wait for all the images to be rendered
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        # turn all the landscape ones
        for group in groups:
            for card in group.cards:
                if card.landscape:
                    out_file = os.path.abspath(f'./build/images/{cleanup(group.name)}/{cleanup(card.name)}.png')
                    subprocess.run(f"convert {out_file} -rotate 90 {out_file}", shell=True)

        # make images with bleed for printing
        for group in groups:
            for card in group.cards:
                add_bleed(group, card)
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        # make pdfs per group
        for group in groups:
            make_pdf(group)

        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

        # make print-n-play pdfs
        print('building print-n-play pdf')
        cards = []
        for group in groups:
            for card in group.cards:
                name = cleanup(card.name) #+ f'[face,{card.count}]'
                filename = f'./build/images/{cleanup(group.name)}/{name}.png'
                cards += [filename] * card.count

        print(cards)
        subprocess.run(f"convert {' '.join(cards)} ./build/pdfs/print-n-play.pdf", shell=True)
        subprocess.run(f"pdfjam ./build/pdfs/print-n-play.pdf -o ./build/pdfs/print-n-play_3x3.pdf --nup 3x3 --scale {10.5/11}", shell=True)
        

        # combined file with all archetypes
        subprocess.run(f"pdftk ./build/pdfs/Archetype* cat output ./build/pdfs/Archetypes.pdf", shell=True)
