from functools import wraps

macros = {}
def register(macro):
    macros[macro.__name__] = macro
    return macro


def on_own_paragraph(macro):
    @wraps(macro)
    def wrapper(*args, **kwargs):
        return '\n\n' + macro(*args, **kwargs) +'\n\n'
    return wrapper

# def maybe_on_own_paragraph(macro):
#     @wraps(macro)
#     def wrapper(*args, **kwargs):
#         return '\n' + macro(*args, **kwargs) +'\n'
#     return wrapper

# ==== macro definitions ====

@register
def attack(strength):
    return f'<span class="attack">attack [{strength}]</span>'

@register
def block():
    return f'<span class="block">block</span>'

@register
def reminder(text):
    return f'<span class="reminder">({text})</span>'

@register
def sequence(*turns):
    return '<div class="sequence">' + ''.join([f'<div class="turn">{turn}</div>' for turn in turns])  + '</div>'

@register
def inspiration(amount='1'):
    return '<span class="inspiration">' + (f'<img src="../../assets/icons/inspiration.png" />' * int(amount)) + '</span>'

@register
def keyword(name, text):
    return f'<span class="keyword">{name}</span> &ndash; ' + reminder(text)

@register
def conjured():
    return keyword('Conjured', 'I appear when another card conjures me and disappear when I leave play.')

@register
def augment():
    return keyword('Augment', 'I appear when I am attached to a card in play, and disappear if I am not.')

# @register
# def signature():
#     return 'You can only claim one signature, and only after losing half your hearts.'

# @register
# def upgrade():
#     return keyword('Upgrade', 'I appear when I am attached to a card in play, and disappear if I am not.')

@register
def invoke_ability(name, ability_text):
    text = ''
    # text += '<div class="spacer"></div>'
    text += '<div class="invoke-ability">'
    text += f'<div class="invoke-name">{name}</div>'
    text += f'<div class="invoke-text">{oninvoke(ability_text)}</div>'
    text += '</div>'
    return text

@register
def invoke():
    return f'<span class="invoke">invoke</span>'

@register
@on_own_paragraph
def Invoke():
    return f'<span class="invoke">Invoke.</span>'

@register
def charge():
    return f'<span class="charge">charge</span>'

@register
def Charge():
    return f'<span class="charge">Charge</span>'

@register
def li(text, name=None):
    if name:
        name, text = text, name
        return f'<em>{name}</em>&nbsp;&ndash;&nbsp;{text}'
    return f'&nbsp;&ndash;&nbsp;{text}'

@register
def b(text):
    return f'<strong>{text}</strong>'

# == triggers ==

@on_own_paragraph
def trigger(prefix, text):
    return f'<span class="trigger"><span class="prefix">{prefix}:</span> {text}</span>'

@register
def endstep(text):
    return trigger('End step', text)

@register
def onreveal(text):
    return trigger('On reveal', text)

@register
def onplay(text):
    return trigger('On play', text)

@register
def equip(text):
    return trigger('Equip', text)

@register
def oninvoke(text):
    return trigger('On invoke', text)


# == on-off effects ==

@register
def orange(text):
    return f'<span class="orange">{b(text)}</span>'

@register
def blue(text):
    return f'<span class="blue">{b(text)}</span>'
