var factor = 2 **(-1/(12*16))

function update_sizes_once() {
    var has_updated = false;
    $('.autofit').each(function () {
        var element = $(this);
        var parent = $(this).parent();
        var font_size = element.css("font-size");
        // console.log(`${element.text()} el: (${element.height()}), parent: ${parent.height()}, size: ${font_size}`);
        if (element.height() > parent.height()) {
            // element.css("font-size", `calc(${font_size} - 0.25mm)`)
            element.css("font-size", `calc(${font_size} * ${factor})`)
            // console.log(`size updated (${font_size}) for: ${parent.attr('class')}`);
            has_updated = true;
        }
    });
    return has_updated;
}

function fit(element) {
    var parent = element. parentNode;
    var font_size = parseFloat(window.getComputedStyle(element).fontSize.slice(0, -2))

    var i = 0
    while (element.offsetHeight > parent.offsetHeight && (i++ < 200)) {
        console.log(font_size, element.offsetHeight, parent.offsetHeight)
        font_size = (font_size*factor) ;
        element.style.fontSize = font_size + 'px';
    }
}

function update_sizes() {
    $('.autofit').each(function () {
        fit($(this)[0]);
    });
}

addEventListener("load", function(){
    // update_sizes_once();
    update_sizes();
});
