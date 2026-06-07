(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCSceneFilter = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function sceneMatches(currentScene, ownScene, data = {}) {
    return !data.sceneId || data.sceneId === currentScene || data.sceneId === ownScene;
  }

  return {
    sceneMatches,
  };
});
