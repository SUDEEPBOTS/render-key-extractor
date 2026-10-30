document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const torToggle = document.getElementById("tor-toggle");
    const torStatusLabel = document.getElementById("tor-status-label");
    const torIpVal = document.getElementById("tor-ip-val");
    const directIpVal = document.getElementById("direct-ip-val");
    const btnRotateTor = document.getElementById("btn-rotate-tor");
    const rotateBefore = document.getElementById("rotate-before");
    
    const extractForm = document.getElementById("extract-form");
    const confirmUrlInput = document.getElementById("confirm-url");
    const keyNameInput = document.getElementById("key-name");
    const btnSubmit = document.getElementById("btn-submit");
    const btnText = document.getElementById("btn-text");
    const btnSpinner = document.getElementById("btn-spinner");
    
    const progressBox = document.getElementById("progress-box");
    const progressText = document.getElementById("progress-text");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    
    const resultCard = document.getElementById("result-card");
    const resultKey = document.getElementById("result-key");
    const btnCopyKey = document.getElementById("btn-copy-key");
    const resultEmail = document.getElementById("result-email");
    const resultWorkspace = document.getElementById("result-workspace");
    const resultOwner = document.getElementById("result-owner");
    const resultIp = document.getElementById("result-ip");
    const curlTestCode = document.getElementById("curl-test-code");
    
    const historyTbody = document.getElementById("history-tbody");
    const btnRefreshHistory = document.getElementById("btn-refresh-history");

    let progressInterval = null;

    // Initialize Network & Tor Status
    async function updateNetworkStatus() {
        try {
            const res = await fetch("/api/tor/status");
            if (res.ok) {
                const data = await res.json();
                directIpVal.textContent = data.direct_ip || "Unavailable";
                torIpVal.textContent = data.tor_ip || "Tor Offline";
                
                if (!data.tor_active) {
                    torToggle.disabled = true;
                    torStatusLabel.textContent = "Tor Service Offline";
                }
            }
        } catch (e) {
            console.error("Failed to load network status", e);
        }
    }

    // Tor Toggle Event
    torToggle.addEventListener("change", () => {
        if (torToggle.checked) {
            torStatusLabel.textContent = "Tor: ON (Anonymized Routing Active)";
            torStatusLabel.style.color = "#c084fc";
            rotateBefore.disabled = false;
        } else {
            torStatusLabel.textContent = "Tor: OFF (Direct Connection)";
            torStatusLabel.style.color = "#94a3b8";
            rotateBefore.disabled = true;
            rotateBefore.checked = false;
        }
    });

    // Rotate Tor IP Button
    btnRotateTor.addEventListener("click", async () => {
        btnRotateTor.disabled = true;
        const originalText = btnRotateTor.textContent;
        btnRotateTor.textContent = "Rotating Circuit...";
        
        try {
            const res = await fetch("/api/tor/rotate", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                torIpVal.textContent = data.new_ip;
                btnRotateTor.textContent = "Rotated: " + data.new_ip;
            } else {
                btnRotateTor.textContent = "Rotation Failed";
            }
        } catch (e) {
            btnRotateTor.textContent = "Error";
        }
        
        setTimeout(() => {
            btnRotateTor.textContent = originalText;
            btnRotateTor.disabled = false;
        }, 3000);
    });

    // Start simulated progress steps
    function startProgressSteps(useTor) {
        progressBox.classList.remove("hidden");
        errorBanner.classList.add("hidden");
        
        const steps = [
            useTor ? "Routing through Tor network & establishing circuit..." : "Connecting to network directly...",
            "Loading Render confirmation link in headless browser...",
            "Validating confirmation token...",
            "Accessing account dashboard settings...",
            "Triggering 'Create API key' modal...",
            "Submitting key credentials...",
            "Extracting generated token...",
            "Verifying token against Render REST API..."
        ];

        let idx = 0;
        progressText.textContent = steps[0];
        progressInterval = setInterval(() => {
            if (idx < steps.length - 1) {
                idx++;
                progressText.textContent = steps[idx];
            }
        }, 2500);
    }

    function stopProgress() {
        if (progressInterval) clearInterval(progressInterval);
        progressBox.classList.add("hidden");
    }

    // Form Submit Event
    extractForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const url = confirmUrlInput.value.trim();
        const name = keyNameInput.value.trim();
        const useTor = torToggle.checked;
        const rotate = rotateBefore.checked;

        if (!url) return;

        // UI Loading State
        btnSubmit.disabled = true;
        btnText.textContent = "Extracting Key...";
        btnSpinner.classList.remove("hidden");
        errorBanner.classList.add("hidden");
        resultCard.classList.add("hidden");

        startProgressSteps(useTor);

        try {
            const res = await fetch("/api/extract", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: url,
                    name: name || null,
                    use_tor: useTor,
                    rotate_before: rotate
                })
            });

            const data = await res.json();
            stopProgress();

            if (!res.ok || !data.success) {
                const msg = data.detail || data.error || "Failed to extract key.";
                showError(msg);
            } else {
                showResult(data);
                loadHistory();
                confirmUrlInput.value = "";
            }
        } catch (err) {
            stopProgress();
            showError("Network connection error: " + err.message);
        } finally {
            btnSubmit.disabled = false;
            btnText.textContent = "Generate & Extract API Key";
            btnSpinner.classList.add("hidden");
        }
    });

    function showError(msg) {
        errorMessage.textContent = msg;
        errorBanner.classList.remove("hidden");
    }

    function showResult(data) {
        resultKey.value = data.api_key;
        resultEmail.textContent = data.email || "N/A";
        resultWorkspace.textContent = data.workspace || "N/A";
        resultOwner.textContent = data.owner_id || "N/A";
        resultIp.textContent = `${data.ip_used} (${data.used_tor ? "Tor Proxy" : "Direct"})`;
        
        curlTestCode.textContent = `curl -H "Authorization: Bearer ${data.api_key}" https://api.render.com/v1/owners`;
        
        resultCard.classList.remove("hidden");
        resultCard.scrollIntoView({ behavior: "smooth" });
    }

    // Copy Key Button
    btnCopyKey.addEventListener("click", () => {
        if (!resultKey.value) return;
        navigator.clipboard.writeText(resultKey.value).then(() => {
            const orig = btnCopyKey.textContent;
            btnCopyKey.textContent = "Copied!";
            btnCopyKey.style.backgroundColor = "#10b981";
            setTimeout(() => {
                btnCopyKey.textContent = orig;
                btnCopyKey.style.backgroundColor = "";
            }, 2000);
        });
    });

    // Download .env Button
    const btnDownloadEnv = document.getElementById("btn-download-env");
    if (btnDownloadEnv) {
        btnDownloadEnv.addEventListener("click", () => {
            if (!resultKey.value) return;
            const url = `/api/download/env?key=${encodeURIComponent(resultKey.value)}&email=${encodeURIComponent(resultEmail.textContent)}&owner_id=${encodeURIComponent(resultOwner.textContent)}`;
            window.location.href = url;
        });
    }

    // History Loader
    async function loadHistory() {
        try {
            const res = await fetch("/api/history?limit=25");
            if (!res.ok) return;
            const records = await res.json();

            if (records.length === 0) {
                historyTbody.innerHTML = '<tr><td colspan="7" class="text-center">No keys extracted yet</td></tr>';
                return;
            }

            historyTbody.innerHTML = records.map(r => {
                const time = r.timestamp ? r.timestamp.replace("T", " ").replace("Z", "").slice(0, 19) : "-";
                const isSuccess = r.status === "SUCCESS";
                const maskedKey = r.api_key ? (r.api_key.slice(0, 10) + "..." + r.api_key.slice(-4)) : "-";
                const routeTag = r.used_tor 
                    ? '<span class="tag tag-tor">Tor</span>' 
                    : '<span class="tag tag-direct">Direct</span>';
                const statusTag = isSuccess 
                    ? '<span class="tag tag-success">Success</span>' 
                    : '<span class="tag tag-failed">Failed</span>';

                return `
                    <tr>
                        <td>${time}</td>
                        <td><code>${maskedKey}</code></td>
                        <td>${r.email || "-"}</td>
                        <td>${r.workspace || "-"}</td>
                        <td>${routeTag}</td>
                        <td>${r.ip_used || "-"}</td>
                        <td>${statusTag}</td>
                    </tr>
                `;
            }).join("");

        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    btnRefreshHistory.addEventListener("click", loadHistory);

    // Initial Calls
    updateNetworkStatus();
    loadHistory();
});
