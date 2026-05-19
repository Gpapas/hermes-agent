(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const { React } = SDK;
  const h = React.createElement;
  const { Card, CardHeader, CardTitle, CardContent, Badge } = SDK.components;

  function ExamplePlugin() {
    return h(
      "div",
      { style: { padding: "1rem" } },
      h(
        Card,
        null,
        h(CardHeader, null, h(CardTitle, null, "Example Plugin")),
        h(
          CardContent,
          null,
          h(Badge, { variant: "secondary" }, "Loaded"),
          h("p", { style: { marginTop: "0.75rem" } }, "Hello from the example plugin!"),
          h("p", { style: { opacity: 0.7, marginTop: "0.5rem" } }, "This plugin exists to verify dashboard plugin loading and auth.")
        )
      )
    );
  }

  window.__HERMES_PLUGINS__.register("example", ExamplePlugin);
})();
