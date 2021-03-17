$(document).ready(function () {
    // click in input field selects contents of field
    $('input').click(function () {
        $(this).select();
    });
    $('.next-up-link').hover(function () {
        $(this).addClass("hover");
    }, function () {
        $(this).removeClass("hover");
    });
});

