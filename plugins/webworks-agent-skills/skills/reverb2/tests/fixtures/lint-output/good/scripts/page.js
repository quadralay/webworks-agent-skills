// page.js stub — models only what lint-output.py reads from the real file.
//
// build_renders_splash_groups() treats the 'splash_groups' lookup below as the
// build's own statement that it expects the Groups Grid container in
// splash.html. Pre-2026.1 page.js has no such lookup, which is how the check
// stays version-tolerant.

Page.SplashGroupsRender = function (param_groups) {
  var groups_nav = Page.window.document.getElementById('splash_groups');
  if (groups_nav === null) {
    return;
  }
};
