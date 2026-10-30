document.addEventListener("DOMContentLoaded", () => {
    // Elements
    const proxyModeSelect = document.getElementById("proxy-mode-select");
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

    // Initialize Network & Proxy Status
    async function updateNetworkStatus() {
        try {
            const res = await fetch("/api/tor/status");
            if (res.ok) {
                const data = await res.json();
                if (directIpVal) directIpVal.textContent = data.direct_ip || "Unavailable";
                
                if (proxyModeSelect && proxyModeSelect.value === "residential") {
                    torIpVal.textContent = "Residential Pool (10 Fresh IPs)";
                } else if (proxyModeSelect && proxyModeSelect.value === "direct") {
                    torIpVal.textContent = data.direct_ip || "Direct IP";
                } else {
                    torIpVal.textContent = data.tor_ip || "Tor Offline";
                }
            }
        } catch (e) {
            console.error("Failed to load network status", e);
        }
    }

    if (proxyModeSelect) {
        proxyModeSelect.addEventListener("change", () => {
            const mode = proxyModeSelect.value;
            if (mode === "tor") {
                if (torToggle) torToggle.checked = true;
                if (rotateBefore) rotateBefore.disabled = false;
                torIpVal.textContent = "Tor SOCKS5 Active";
            } else if (mode === "residential") {
                if (torToggle) torToggle.checked = false;
                if (rotateBefore) rotateBefore.disabled = true;
                torIpVal.textContent = "Residential Pool (10 Fresh IPs)";
            } else {
                if (torToggle) torToggle.checked = false;
                if (rotateBefore) rotateBefore.disabled = true;
                torIpVal.textContent = directIpVal ? directIpVal.textContent : "Direct Connection";
            }
        });
    }

    // Tor Toggle Event (Sync)
    if (torToggle) {
        torToggle.addEventListener("change", () => {
            if (torToggle.checked) {
                if (proxyModeSelect) proxyModeSelect.value = "tor";
                if (rotateBefore) rotateBefore.disabled = false;
            } else {
                if (proxyModeSelect) proxyModeSelect.value = "residential";
                if (rotateBefore) rotateBefore.disabled = true;
            }
        });
    }

    // Rotate Tor IP Button
    btnRotateTor.addEventListener("click", async () => {
        btnRotateTor.disabled = true;
        const originalText = btnRotateTor.textContent;
        btnRotateTor.textContent = "Rotating / Testing...";
        
        try {
            const res = await fetch("/api/tor/rotate", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                if (proxyModeSelect && proxyModeSelect.value === "tor") {
                    torIpVal.textContent = data.new_ip;
                }
                btnRotateTor.textContent = "Rotated: " + data.new_ip;
            } else {
                btnRotateTor.textContent = "Rotation Ready";
            }
        } catch (e) {
            btnRotateTor.textContent = "Ready";
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

    // Unified Direct Extraction Function (No Paste, 100% Automated)
    async function executeExtraction(url, keyName = null) {
        if (!url) return;

        const proxyMode = proxyModeSelect ? proxyModeSelect.value : "residential";
        const useTor = (proxyMode === "tor") || (torToggle && torToggle.checked);
        const rotate = rotateBefore && rotateBefore.checked;

        // UI Loading State
        btnSubmit.disabled = true;
        btnText.textContent = "Extracting...";
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
                    name: keyName || null,
                    use_tor: useTor,
                    rotate_before: rotate,
                    proxy_mode: proxyMode
                })
            });

            const data = await res.json();
            stopProgress();

            if (!res.ok || !data.success) {
                const msg = data.detail || data.error || "Failed to extract key.";
                showError(msg);
                mailListenerStatus.textContent = "Extraction failed: " + msg;
                mailListenerStatus.style.color = "#ef4444";
            } else {
                mailListenerStatus.textContent = "Render API Key successfully generated & verified!";
                mailListenerStatus.style.color = "#10b981";
                showResult(data);
                loadHistory();
                if (confirmUrlInput) confirmUrlInput.value = "";
                // Store Mode batch hook
                await onKeyExtractedInBatch(data);
            }
        } catch (err) {
            stopProgress();
            showError("Network connection error: " + err.message);
            mailListenerStatus.textContent = "Error: " + err.message;
            mailListenerStatus.style.color = "#ef4444";
        } finally {
            btnSubmit.disabled = false;
            btnText.textContent = "Extract From Pasted Link";
            btnSpinner.classList.add("hidden");
        }
    }

    // Manual Form Submit Event (Fallback Only)
    extractForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = confirmUrlInput.value.trim();
        const name = keyNameInput.value.trim();
        if (url) {
            await executeExtraction(url, name);
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

    // Mail Assistant Elements
    const mailProviderSelect = document.getElementById("mail-provider-select");
    const mailDomainSelect = document.getElementById("mail-domain-select");
    const btnGenerateMail = document.getElementById("btn-generate-mail");
    const credentialsPanel = document.getElementById("credentials-panel");
    const autoEmailInput = document.getElementById("auto-email");
    const autoPasswordInput = document.getElementById("auto-password");
    const btnCopyEmail = document.getElementById("btn-copy-email");
    const btnCopyPassword = document.getElementById("btn-copy-password");
    const mailListenerStatus = document.getElementById("mail-listener-status");

    let mailPollInterval = null;
    let mailCheckCount = 0;
    let currentMailToken = null;
    let currentMailProvider = "yuki";

    // Dynamic Domain Loading per Provider
    if (mailProviderSelect && mailDomainSelect) {
        mailProviderSelect.addEventListener("change", async () => {
            currentMailProvider = mailProviderSelect.value;
            try {
                const res = await fetch(`/api/mail/domains?provider=${encodeURIComponent(currentMailProvider)}`);
                if (res.ok) {
                    const data = await res.json();
                    mailDomainSelect.innerHTML = data.domains.map(d => `<option value="${d}">${d}</option>`).join("");
                }
            } catch (e) {
                console.error("Failed to load domains", e);
            }
        });
    }

    if (btnGenerateMail) {
        btnGenerateMail.addEventListener("click", async () => {
            btnGenerateMail.disabled = true;
            btnGenerateMail.textContent = "Generating...";
            
            if (mailPollInterval) clearInterval(mailPollInterval);
            mailCheckCount = 0;

            const provider = mailProviderSelect ? mailProviderSelect.value : "yuki";
            const domain = mailDomainSelect ? mailDomainSelect.value : null;

            try {
                const res = await fetch("/api/mail/generate", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider: provider, domain: domain })
                });
                const data = await res.json();
                
                if (res.ok && data.success) {
                    currentMailToken = data.token;
                    currentMailProvider = data.provider || provider;
                    autoEmailInput.value = data.email;
                    autoPasswordInput.value = data.password;
                    credentialsPanel.classList.remove("hidden");
                    
                    mailListenerStatus.textContent = `Listening on ${data.email}... (Checked 0 times)`;
                    mailListenerStatus.style.color = "#38bdf8";
                    
                    // Start polling for incoming confirmation link
                    startMailListener(data.token, currentMailProvider);
                } else {
                    alert("Failed to generate mailbox: " + (data.detail || data.error));
                }
            } catch (err) {
                alert("Network error creating mailbox: " + err.message);
            } finally {
                btnGenerateMail.disabled = false;
                btnGenerateMail.textContent = "Generate New Credentials";
            }
        });
    }

    function startMailListener(token, provider) {
        if (mailPollInterval) clearInterval(mailPollInterval);
        
        mailPollInterval = setInterval(async () => {
            mailCheckCount++;
            mailListenerStatus.textContent = `Listening for Render confirmation email... (Checked ${mailCheckCount} times)`;

            try {
                const res = await fetch(`/api/mail/check?token=${encodeURIComponent(token)}&provider=${encodeURIComponent(provider)}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.found && data.confirm_url) {
                        clearInterval(mailPollInterval);
                        mailListenerStatus.textContent = "Confirmation email detected! Auto-starting key extraction...";
                        mailListenerStatus.style.color = "#10b981";

                        // Directly start extraction without any manual copy-paste!
                        if (confirmUrlInput) confirmUrlInput.value = data.confirm_url;
                        await executeExtraction(data.confirm_url);
                    }
                }
            } catch (e) {
                console.warn("Mail check error:", e);
            }

            // Stop polling after 180 checks (6 minutes)
            if (mailCheckCount >= 180) {
                clearInterval(mailPollInterval);
                mailListenerStatus.textContent = "Listening timed out (6 min). Click generate to try again.";
                mailListenerStatus.style.color = "#ef4444";
            }
        }, 2000);
    }

    if (btnCopyEmail) {
        btnCopyEmail.addEventListener("click", () => {
            if (!autoEmailInput.value) return;
            navigator.clipboard.writeText(autoEmailInput.value).then(() => {
                const orig = btnCopyEmail.textContent;
                btnCopyEmail.textContent = "Copied!";
                btnCopyEmail.style.backgroundColor = "#10b981";
                setTimeout(() => {
                    btnCopyEmail.textContent = orig;
                    btnCopyEmail.style.backgroundColor = "";
                }, 1500);
            });
        });
    }

    if (btnCopyPassword) {
        btnCopyPassword.addEventListener("click", () => {
            if (!autoPasswordInput.value) return;
            navigator.clipboard.writeText(autoPasswordInput.value).then(() => {
                const orig = btnCopyPassword.textContent;
                btnCopyPassword.textContent = "Copied!";
                btnCopyPassword.style.backgroundColor = "#10b981";
                setTimeout(() => {
                    btnCopyPassword.textContent = orig;
                    btnCopyPassword.style.backgroundColor = "";
                }, 1500);
            });
        });
    }

    // Store Mode & Yukisbox
    const batchTargetSelect = document.getElementById("batch-target-select");
    const batchCountDisplay = document.getElementById("batch-count-display");
    const batchTargetDisplay = document.getElementById("batch-target-display");
    const batchProgressBar = document.getElementById("batch-progress-bar");
    const btnUploadYukisboxManual = document.getElementById("btn-upload-yukisbox-manual");
    const yukisboxResultBox = document.getElementById("yukisbox-result-box");
    const yukisboxFileUrl = document.getElementById("yukisbox-file-url");
    const yukisboxRawUrl = document.getElementById("yukisbox-raw-url");

    let collectedBatchKeys = [];

    if (batchTargetSelect) {
        batchTargetSelect.addEventListener("change", () => {
            batchTargetDisplay.textContent = batchTargetSelect.value;
            updateBatchProgress();
        });
    }

    function updateBatchProgress() {
        const target = parseInt(batchTargetSelect.value, 10) || 5;
        const current = collectedBatchKeys.length;
        batchCountDisplay.textContent = current;
        batchTargetDisplay.textContent = target;
        const pct = Math.min(100, Math.round((current / target) * 100));
        batchProgressBar.style.width = pct + "%";
    }

    async function onKeyExtractedInBatch(keyData) {
        collectedBatchKeys.push(keyData);
        updateBatchProgress();

        const target = parseInt(batchTargetSelect.value, 10) || 5;
        if (collectedBatchKeys.length >= target) {
            // Auto-upload completed batch to Yukisbox!
            await triggerYukisboxUpload(collectedBatchKeys, `Render_Batch_${collectedBatchKeys.length}_Keys`);
            collectedBatchKeys = [];
            updateBatchProgress();
        } else {
            // Automatically queue and generate next email credentials!
            if (btnGenerateMail) {
                setTimeout(() => {
                    btnGenerateMail.click();
                }, 1500);
            }
        }
    }

    async function triggerYukisboxUpload(keysList = null, title = null) {
        try {
            const body = {};
            if (keysList && keysList.length > 0) {
                body.keys = keysList;
            }
            if (title) body.title = title;

            const res = await fetch("/api/yukisbox/upload", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });

            const data = await res.json();
            if (res.ok && data.success) {
                yukisboxFileUrl.href = data.url;
                yukisboxFileUrl.textContent = data.url;
                yukisboxRawUrl.href = data.raw_url;
                yukisboxRawUrl.textContent = data.raw_url;
                yukisboxResultBox.classList.remove("hidden");
                yukisboxResultBox.scrollIntoView({ behavior: "smooth" });
            } else {
                alert("Yukisbox upload failed: " + (data.detail || data.error));
            }
        } catch (e) {
            alert("Yukisbox upload error: " + e.message);
        }
    }

    if (btnUploadYukisboxManual) {
        btnUploadYukisboxManual.addEventListener("click", () => {
            btnUploadYukisboxManual.disabled = true;
            btnUploadYukisboxManual.textContent = "Uploading to Yukisbox...";
            triggerYukisboxUpload(collectedBatchKeys.length > 0 ? collectedBatchKeys : null)
                .finally(() => {
                    btnUploadYukisboxManual.disabled = false;
                    btnUploadYukisboxManual.textContent = "Upload Keys to Yukisbox Now";
                });
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
                const isResidential = !r.used_tor && r.ip_used && !r.ip_used.startsWith("74.220");
                const routeTag = r.used_tor 
                    ? '<span class="tag tag-tor">Tor</span>' 
                    : (isResidential ? '<span class="tag tag-success" style="background:#065f46;color:#6ee7b7;">Residential</span>' : '<span class="tag tag-direct">Direct</span>');
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
