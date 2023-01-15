function scale() {
    var card = document.getElementsByClassName('card')[0];

    var xscale = window.innerWidth / card.offsetWidth;
    var yscale = window.innerHeight / card.offsetHeight;

    var scale = Math.min(xscale, yscale);
    document.body.style.transform = 'scale(' + scale + ')';
}

addEventListener("DOMContentLoaded", scale);
window.addEventListener("resize", scale);
