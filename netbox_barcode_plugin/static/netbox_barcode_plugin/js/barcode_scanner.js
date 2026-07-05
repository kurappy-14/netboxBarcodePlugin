(function () {
  "use strict";

  const state = {
    scanner: null,
    scanning: false,
    torchOn: false,
    currentCableId: null,
    lastLookupPayload: null,
    statusUrlTemplate: "",
    lookupUrl: "",
    csrfToken: "",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function getCookie(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + "=")) {
        return decodeURIComponent(trimmed.substring(name.length + 1));
      }
    }
    return null;
  }

  function clearNode(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  const STATUS_BADGE_CLASS = {
    not_created: "text-bg-secondary",
    configured: "text-bg-warning",
    laid: "text-bg-success",
  };

  function textEl(tag, text, className) {
    const el = document.createElement(tag);
    if (className) {
      el.className = className;
    }
    el.textContent = text == null ? "" : String(text);
    return el;
  }

  function showAlert(message, type) {
    const alerts = $("barcode-alerts");
    const div = document.createElement("div");
    div.className = "alert alert-" + (type || "info") + " alert-dismissible fade show";
    div.setAttribute("role", "alert");

    const span = document.createElement("span");
    span.textContent = message;
    div.appendChild(span);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn-close";
    button.setAttribute("data-bs-dismiss", "alert");
    button.setAttribute("aria-label", "閉じる");
    div.appendChild(button);

    alerts.appendChild(div);
  }

  function resetAlerts() {
    clearNode($("barcode-alerts"));
  }

  async function fetchJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-CSRFToken": state.csrfToken || getCookie("csrftoken") || "",
      },
      body: JSON.stringify(body),
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = {
        success: false,
        error: "サーバー応答をJSONとして解析できません。",
        code: "invalid_response",
      };
    }

    if (!response.ok || !payload.success) {
      const message = payload && payload.error ? payload.error : "通信に失敗しました。";
      const err = new Error(message);
      err.payload = payload;
      err.status = response.status;
      throw err;
    }

    return payload;
  }

  async function stopScanner() {
    if (!state.scanner || !state.scanning) {
      return;
    }
    try {
      await state.scanner.stop();
    } catch (error) {
      // Stopping may fail when the camera was already released. It is safe to
      // continue because the UI is switching to result/manual mode.
    }
    state.scanning = false;
    state.torchOn = false;
    updateTorchButton(false);
  }

  function updateTorchButton(supported) {
    const torchButton = $("torch-button");
    const torchMessage = $("torch-message");
    if (!torchButton) {
      return;
    }

    if (!supported) {
      torchButton.disabled = true;
      torchButton.textContent = "ライト非対応";
      torchMessage.classList.remove("d-none");
      return;
    }

    torchButton.disabled = !state.scanning;
    torchButton.textContent = state.torchOn ? "ライトOFF" : "ライトON";
    torchMessage.classList.add("d-none");
  }

  function detectTorchSupport() {
    try {
      if (!state.scanner || typeof state.scanner.getRunningTrackCapabilities !== "function") {
        updateTorchButton(false);
        return false;
      }
      const caps = state.scanner.getRunningTrackCapabilities();
      const supported = Boolean(caps && caps.torch);
      updateTorchButton(supported);
      return supported;
    } catch (error) {
      updateTorchButton(false);
      return false;
    }
  }

  async function toggleTorch() {
    if (!state.scanner || !state.scanning) {
      return;
    }
    try {
      state.torchOn = !state.torchOn;
      await state.scanner.applyVideoConstraints({
        advanced: [{ torch: state.torchOn }],
      });
      updateTorchButton(true);
    } catch (error) {
      state.torchOn = false;
      updateTorchButton(false);
      showAlert("ライト制御に失敗しました。スキャンは継続できます。", "warning");
    }
  }

  async function startScanner() {
    resetAlerts();
    if (typeof Html5Qrcode === "undefined") {
      showAlert("バーコード読み取りライブラリを読み込めません。手入力で検索してください。", "warning");
      return;
    }

    $("rescan-button").disabled = true;
    $("start-scan-button").disabled = true;
    clearResult();

    if (!state.scanner) {
      state.scanner = new Html5Qrcode("reader");
    }

    const formats = [];
    if (typeof Html5QrcodeSupportedFormats !== "undefined" && Html5QrcodeSupportedFormats.CODE_128) {
      formats.push(Html5QrcodeSupportedFormats.CODE_128);
    }

    const config = {
      fps: 10,
      qrbox: function (viewfinderWidth, viewfinderHeight) {
        const width = Math.floor(viewfinderWidth * 0.85);
        const height = Math.min(180, Math.floor(viewfinderHeight * 0.45));
        return { width, height };
      },
    };
    if (formats.length) {
      config.formatsToSupport = formats;
    }

    try {
      await state.scanner.start(
        { facingMode: { exact: "environment" } },
        config,
        handleScanSuccess,
        function () {}
      );
    } catch (exactError) {
      try {
        await state.scanner.start(
          { facingMode: "environment" },
          config,
          handleScanSuccess,
          function () {}
        );
      } catch (fallbackError) {
        $("start-scan-button").disabled = false;
        updateTorchButton(false);
        showAlert("カメラを起動できません。手入力で検索してください。", "warning");
        return;
      }
    }

    state.scanning = true;
    $("start-scan-button").disabled = true;
    detectTorchSupport();
  }

  async function handleScanSuccess(decodedText) {
    await stopScanner();
    $("rescan-button").disabled = false;
    $("start-scan-button").disabled = false;
    await lookupBarcode(decodedText);
  }

  async function lookupBarcode(code) {
    resetAlerts();
    try {
      const payload = await fetchJson(state.lookupUrl, { code });
      renderLookupResult(payload);
      showAlert("照会しました。", "success");
    } catch (error) {
      clearResult();
      showAlert(error.message || "照会に失敗しました。", "danger");
    }
  }

  function clearResult() {
    state.currentCableId = null;
    const card = $("result-card");
    const content = $("result-content");
    if (content) {
      clearNode(content);
    }
    if (card) {
      card.classList.add("d-none");
    }
  }

  function renderLookupResult(payload) {
    const card = $("result-card");
    const content = $("result-content");
    clearNode(content);
    state.lastLookupPayload = payload;
    state.currentCableId = payload.cable.id;

    content.appendChild(renderCableSection(payload));
    content.appendChild(renderEndpointSummary(payload.endpoints));
    content.appendChild(renderTraceGrid(payload.trace, payload.trace_endpoints));

    card.classList.remove("d-none");
  }

  function renderCableSection(payload) {
    const section = document.createElement("section");
    section.className = "result-section";
    section.appendChild(textEl("h5", "ケーブル情報", "result-section-title"));

    const cable = payload.cable;
    const dl = document.createElement("dl");
    dl.className = "row mb-2";

    addDefinition(dl, "ケーブル名", cableLink(cable));
    addDefinition(dl, "バーコード", textEl("span", cable.barcode || "-"));
    addDefinition(dl, "現在のステータス", statusDisplay(cable.status));

    if (payload.can_update) {
      addDefinition(dl, "ステータス更新", statusUpdateForm(payload.status_options, cable.status.value));
    } else {
      addDefinition(dl, "更新権限", textEl("span", "このケーブルを更新する権限がありません。", "text-muted"));
    }

    section.appendChild(dl);

    const matchedBy = payload.matched_by || [];
    if (matchedBy.length) {
      const matched = textEl("p", "一致項目: " + matchedBy.join(", "), "result-meta text-muted small mb-0");
      section.appendChild(matched);
    }

    return section;
  }

  function renderEndpointSummary(endpoints) {
    const section = document.createElement("section");
    section.className = "result-section endpoint-summary";
    section.appendChild(textEl("h5", "接続先サマリー（直結ポート）", "result-section-title"));

    const row = document.createElement("div");
    row.className = "row g-2 align-items-stretch";

    const aCol = document.createElement("div");
    aCol.className = "col-12 col-md-5";
    aCol.appendChild(endpointSummaryCard("A端", endpoints && endpoints.a_side));

    const arrowCol = document.createElement("div");
    arrowCol.className = "col-12 col-md-2 d-flex align-items-center justify-content-center";
    const arrow = document.createElement("div");
    arrow.className = "endpoint-arrow";
    arrow.setAttribute("aria-hidden", "true");
    arrow.textContent = "⇔";
    arrowCol.appendChild(arrow);

    const bCol = document.createElement("div");
    bCol.className = "col-12 col-md-5";
    bCol.appendChild(endpointSummaryCard("B端", endpoints && endpoints.b_side));

    row.appendChild(aCol);
    row.appendChild(arrowCol);
    row.appendChild(bCol);
    section.appendChild(row);

    return section;
  }

  function endpointSummaryCard(sideLabel, endpoint) {
    const card = document.createElement("div");
    card.className = "endpoint-card h-100";

    const label = textEl("div", sideLabel, "endpoint-side-label");
    card.appendChild(label);

    const body = document.createElement("div");
    body.className = "endpoint-value";
    body.appendChild(endpoint ? objectRefNode(endpoint) : textEl("span", "未接続", "text-muted"));
    card.appendChild(body);

    return card;
  }

  function cableLink(cable) {
    if (!cable.url) {
      return textEl("span", cable.display || cable.label || "-");
    }
    const a = document.createElement("a");
    a.href = cable.url;
    a.textContent = cable.display || cable.label || "-";
    return a;
  }

  function statusDisplay(status) {
    const value = status && status.value ? status.value : "";
    const badgeClass = STATUS_BADGE_CLASS[value] || "text-bg-info";
    const span = textEl("span", status && status.label ? status.label : "-", "badge " + badgeClass + " status-badge");
    span.dataset.statusValue = value;
    return span;
  }

  function statusUpdateForm(options, currentValue) {
    const wrapper = document.createElement("div");
    wrapper.className = "d-flex gap-2 flex-wrap";

    const select = document.createElement("select");
    select.id = "status-select";
    select.className = "form-select w-auto";
    for (const option of options || []) {
      const opt = document.createElement("option");
      opt.value = option.value;
      opt.textContent = option.label;
      if (option.value === currentValue) {
        opt.selected = true;
      }
      select.appendChild(opt);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-primary";
    button.textContent = "更新";
    button.addEventListener("click", updateStatus);

    wrapper.appendChild(select);
    wrapper.appendChild(button);
    return wrapper;
  }

  function addDefinition(dl, labelText, valueNode) {
    const dt = textEl("dt", labelText, "col-sm-4");
    const dd = document.createElement("dd");
    dd.className = "col-sm-8";
    dd.appendChild(valueNode);
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  function renderTraceGrid(trace, endpoints) {
    const section = document.createElement("section");
    section.className = "result-section";
    section.appendChild(textEl("h5", "経路詳細", "result-section-title"));

    const row = document.createElement("div");
    row.className = "row g-3";

    const aCol = document.createElement("div");
    aCol.className = "col-12 col-lg-6";
    aCol.appendChild(renderTraceSection("A端側の経路", trace && trace.a_side, endpoints && endpoints.a_side));

    const bCol = document.createElement("div");
    bCol.className = "col-12 col-lg-6";
    bCol.appendChild(renderTraceSection("B端側の経路", trace && trace.b_side, endpoints && endpoints.b_side));

    row.appendChild(aCol);
    row.appendChild(bCol);
    section.appendChild(row);

    return section;
  }

  function renderTraceSection(title, items, endpoint) {
    const section = document.createElement("section");
    section.className = "trace-panel";

    const details = document.createElement("details");
    details.className = "trace-details";

    const summary = document.createElement("summary");
    summary.className = "trace-summary";
    summary.appendChild(textEl("span", title, "trace-title"));
    summary.appendChild(textEl("span", traceCountLabel(items), "badge text-bg-light trace-count"));
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "trace-body";

    if (!items || !items.length) {
      body.appendChild(textEl("p", "未接続または経路情報がありません。", "text-muted mb-2"));
    } else {
      const ol = document.createElement("ol");
      ol.className = "trace-list";
      for (const item of items) {
        const li = document.createElement("li");
        li.appendChild(objectRefNode(item));
        ol.appendChild(li);
      }
      body.appendChild(ol);
    }

    const endpointLabel = document.createElement("p");
    endpointLabel.className = "trace-endpoint mt-2 mb-0";
    endpointLabel.appendChild(textEl("strong", "末端の接続先: "));
    endpointLabel.appendChild(endpoint ? objectRefNode(endpoint) : textEl("span", "未接続", "text-muted"));
    body.appendChild(endpointLabel);

    details.appendChild(body);
    section.appendChild(details);

    return section;
  }

  function traceCountLabel(items) {
    const count = items && items.length ? items.length : 0;
    return count + "件";
  }

  function objectRefNode(ref) {
    const fragment = document.createDocumentFragment();
    if (ref.url) {
      const a = document.createElement("a");
      a.href = ref.url;
      a.textContent = ref.name || "-";
      fragment.appendChild(a);
    } else {
      fragment.appendChild(textEl("span", ref.name || "-"));
    }
    const meta = [];
    if (ref.type) {
      meta.push(ref.type);
    }
    if (ref.device) {
      meta.push(ref.device);
    }
    if (meta.length) {
      fragment.appendChild(textEl("span", " (" + meta.join(" / ") + ")", "text-muted"));
    }
    const span = document.createElement("span");
    span.appendChild(fragment);
    return span;
  }

  async function updateStatus() {
    const select = $("status-select");
    if (!select || !state.currentCableId) {
      return;
    }
    resetAlerts();
    const url = state.statusUrlTemplate.replace("__CABLE_ID__", String(state.currentCableId));
    try {
      const payload = await fetchJson(url, { cable_status: select.value });
      if (state.lastLookupPayload) {
        state.lastLookupPayload.cable = payload.cable;
        state.lastLookupPayload.can_update = payload.can_update;
        renderLookupResult(state.lastLookupPayload);
      }
      showAlert(payload.message || "更新しました。", "success");
    } catch (error) {
      showAlert(error.message || "更新に失敗しました。", "danger");
    }
  }

  function bindEvents() {
    const root = document.querySelector(".barcode-plugin");
    if (!root) {
      return;
    }
    state.lookupUrl = root.dataset.lookupUrl;
    state.statusUrlTemplate = root.dataset.statusUrlTemplate;
    state.csrfToken = root.dataset.csrfToken || "";

    $("start-scan-button").addEventListener("click", startScanner);
    $("rescan-button").addEventListener("click", startScanner);
    $("torch-button").addEventListener("click", toggleTorch);
    $("manual-search-form").addEventListener("submit", async function (event) {
      event.preventDefault();
      await stopScanner();
      $("rescan-button").disabled = false;
      $("start-scan-button").disabled = false;
      await lookupBarcode($("manual-code").value);
    });
  }

  document.addEventListener("DOMContentLoaded", bindEvents);
})();
