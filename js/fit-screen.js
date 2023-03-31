function scale_card() {
    var card = document.getElementsByClassName('card')[0];
    if (card == undefined)
        return

    var xscale = window.innerWidth / card.offsetWidth;
    var yscale = window.innerHeight / card.offsetHeight;

    var scale = Math.min(xscale, yscale);
    // document.body.style.transform = 'scale(' + scale + ')';
    card.parentElement.style.transform = 'scale(' + scale + ')';

}

addEventListener("DOMContentLoaded", scale_card);
window.addEventListener("resize", scale_card);


function scale_carousel() {
    // var card = document.getElementsByClassName('single-card')[0];
    // var max = Math.max(card.offsetWidth, card.offsetHeight);
    // var xscale = window.innerWidth / max;
    // var yscale = window.innerHeight / max;

    // document.body.style.transform = 'scale(' + scale + ')';
    var card = document.getElementsByClassName('single-card')[0];
    if (card == undefined)
        return

    var xscale = window.innerWidth / card.offsetWidth;
    var yscale = window.innerHeight / card.offsetHeight;

    var scale = Math.min(xscale, yscale);
    document.body.style.transform = 'scale(' + scale + ')';
    // card.parentElement.style.transform = 'scale(' + scale + ')';
}

addEventListener("DOMContentLoaded", scale_carousel);
window.addEventListener("resize", scale_carousel);
