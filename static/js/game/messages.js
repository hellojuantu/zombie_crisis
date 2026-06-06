(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ZCMessages = api;
})(typeof globalThis !== 'undefined' ? globalThis : window, function () {
  function stageFailedMessage(wave, reason) {
    const label = `第 ${wave || 1} 关`;
    if (reason === 'abandon') return `${label}已放弃，重新部署`;
    if (reason === 'extraction_failed') return `${label}撤离失败，重新部署`;
    return `${label}失败，重新部署`;
  }

  return {
    stageFailedMessage,
  };
});
