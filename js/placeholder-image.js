addEventListener("DOMContentLoaded", function(){
    // add placeholder class when image doesn't load
    document.querySelectorAll('.art').forEach(el => {
        el.children[0].onerror = () => el.classList.add("placeholder")
    })

    // recolor images
    // document.querySelectorAll('.art').forEach(el => {
    //     img = el.children[0];
    //     url = img.src;
    //     console.log(img)
    //     img.style["background-color"] = "#000";
    //     img.style["mask-image"] = "url('" + url + "')";
    //     img.style["mask-size"] = "cover";
    //     img.style["mask-size"] = "cover";
    //     object-fit: cover;
    // })
});
