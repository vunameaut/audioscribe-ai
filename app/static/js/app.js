// AudioScribe AI - Core Interactive Engine
document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentJobId = null;
    let jobData = null;
    let pollInterval = null;
    let processStartTime = null;
    let activeFilterSpeaker = "all";
    let activeSearchTerm = "";
    let renamingOldName = null;

    // DOM Elements - Navigation & Settings
    const gpuBadge = document.getElementById("gpu-badge");
    const gpuText = document.getElementById("gpu-text");
    const btnOpenSettings = document.getElementById("btn-open-settings");
    const apiKeyIndicator = document.getElementById("api-key-indicator");
    const modalSettings = document.getElementById("modal-settings");
    const btnCloseSettingsModal = document.getElementById("btn-close-settings-modal");
    const btnCancelSettings = document.getElementById("btn-cancel-settings");
    const btnSaveSettings = document.getElementById("btn-save-settings");
    const inputApiKey = document.getElementById("input-api-key");
    const selectGeminiModel = document.getElementById("select-gemini-model");
    const btnToggleKeyVis = document.getElementById("btn-toggle-key-visibility");

    // DOM Elements - Upload & Setup
    const setupSection = document.getElementById("setup-section");
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const fileInfoPreview = document.getElementById("file-info-preview");
    const fileNameEl = document.getElementById("file-name");
    const fileSizeEl = document.getElementById("file-size");
    const fileDurationEl = document.getElementById("file-duration");
    const fileFormatEl = document.getElementById("file-format");
    const btnRemoveFile = document.getElementById("btn-remove-file");
    const audioPreviewContainer = document.getElementById("audio-preview-container");
    const audioPreviewPlayer = document.getElementById("audio-preview-player");
    const modeCards = document.querySelectorAll(".mode-card");
    const inputSpeakersCount = document.getElementById("input-speakers-count");
    const inputSpeakerHints = document.getElementById("input-speaker-hints");
    const inputMeetingContext = document.getElementById("input-meeting-context");
    const btnStartProcess = document.getElementById("btn-start-process");

    // DOM Elements - Progress
    const progressSection = document.getElementById("progress-section");
    const progressMessage = document.getElementById("progress-message");
    const progressSub = document.getElementById("progress-sub");
    const timerDisplay = document.getElementById("timer-display");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressPct = document.getElementById("progress-pct");
    const step1 = document.getElementById("step-1");
    const step2 = document.getElementById("step-2");
    const step3 = document.getElementById("step-3");
    const line1 = document.getElementById("line-1");
    const line2 = document.getElementById("line-2");

    // DOM Elements - Results
    const resultsSection = document.getElementById("results-section");
    const resultMeetingTitle = document.getElementById("result-meeting-title");
    const resDuration = document.getElementById("res-duration");
    const resSpeakersCount = document.getElementById("res-speakers-count");
    const resTurnsCount = document.getElementById("res-turns-count");
    const btnRestart = document.getElementById("btn-restart");

    // Audio Player Bar
    const mainAudioPlayer = document.getElementById("main-audio-player");
    const btnPlayerPlay = document.getElementById("btn-player-play");
    const playerCurrentTime = document.getElementById("player-current-time");
    const playerTotalTime = document.getElementById("player-total-time");
    const playerScrubber = document.getElementById("player-scrubber");
    const playerSpeakingBadge = document.getElementById("player-speaking-indicator");
    const speakingNowName = document.getElementById("speaking-now-name");
    const btnSpeed = document.getElementById("btn-speed");
    const playerVolume = document.getElementById("player-volume");

    // Tabs
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const tabTranscriptCount = document.getElementById("tab-transcript-count");

    // Tab 1 Elements
    const sumOverview = document.getElementById("sum-overview");
    const sumTagsContainer = document.getElementById("sum-tags-container");
    const sumDecisionsList = document.getElementById("sum-decisions-list");
    const sumActionsBody = document.getElementById("sum-actions-body");
    const sumSpeakersViewpoints = document.getElementById("sum-speakers-viewpoints");
    const sumTopicsContainer = document.getElementById("sum-topics-container");

    // Tab 2 Elements
    const transcriptSearch = document.getElementById("transcript-search");
    const btnClearSearch = document.getElementById("btn-clear-search");
    const speakerFilterPills = document.getElementById("speaker-filter-pills");
    const transcriptFeed = document.getElementById("transcript-feed");

    // Tab 3 Elements
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const btnSendChat = document.getElementById("btn-send-chat");
    const quickPromptBtns = document.querySelectorAll(".quick-prompt-btn");

    // Rename Modal Elements
    const modalRename = document.getElementById("modal-rename-speaker");
    const btnCloseRenameModal = document.getElementById("btn-close-rename-modal");
    const btnCancelRename = document.getElementById("btn-cancel-rename");
    const btnConfirmRename = document.getElementById("btn-confirm-rename");
    const renameOldName = document.getElementById("rename-old-name");
    const renameNewName = document.getElementById("rename-new-name");

    // Toast
    const toastEl = document.getElementById("toast");
    const toastMsgEl = document.getElementById("toast-message");

    // Initialization
    loadSettings();
    checkSystemStatus();

    // ----------------------------------------------------
    // SYSTEM STATUS & SETTINGS
    // ----------------------------------------------------
    async function checkSystemStatus() {
        try {
            const res = await fetch("/api/status");
            const data = await res.json();
            if (data.has_gpu) {
                gpuText.textContent = data.gpu_name;
                gpuBadge.classList.remove("hidden");
            } else {
                gpuText.textContent = "CPU Mode";
            }
        } catch (e) {
            console.warn("Status check failed", e);
        }
    }

    function loadSettings() {
        const savedKey = localStorage.getItem("gemini_api_key") || "";
        let savedModel = localStorage.getItem("gemini_model") || "gemini-3.5-flash";
        if (savedModel === "gemini-2.5-flash") {
            savedModel = "gemini-3.5-flash";
            localStorage.setItem("gemini_model", savedModel);
        }
        inputApiKey.value = savedKey;
        selectGeminiModel.value = savedModel;
        updateApiKeyBadge(savedKey);
    }

    function updateApiKeyBadge(key) {
        if (key && key.trim().length > 10) {
            apiKeyIndicator.classList.add("configured");
            apiKeyIndicator.title = "Đã cấu hình Gemini API Key";
        } else {
            apiKeyIndicator.classList.remove("configured");
            apiKeyIndicator.title = "Chưa cấu hình API Key";
        }
    }

    btnOpenSettings.addEventListener("click", () => {
        modalSettings.classList.remove("hidden");
    });
    btnCloseSettingsModal.addEventListener("click", () => modalSettings.classList.add("hidden"));
    btnCancelSettings.addEventListener("click", () => modalSettings.classList.add("hidden"));

    const btnVerifyKey = document.getElementById("btn-verify-key");
    if (btnVerifyKey) {
        btnVerifyKey.addEventListener("click", async () => {
            const key = inputApiKey.value.trim();
            if (!key) {
                showToast("Vui lòng nhập API Key để kiểm tra!", "error");
                return;
            }
            btnVerifyKey.disabled = true;
            btnVerifyKey.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra...';
            try {
                const res = await fetch("/api/verify-key", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ api_key: key })
                });
                const data = await res.json();
                if (data.valid) {
                    showToast(data.message, "success");
                    updateApiKeyBadge(key);
                } else {
                    showToast(data.message, "error");
                }
            } catch (e) {
                showToast("Không thể kết nối tới máy chủ kiểm tra", "error");
            } finally {
                btnVerifyKey.disabled = false;
                btnVerifyKey.innerHTML = '<i class="fa-solid fa-vial-circle-check"></i> Kiểm Tra Key';
            }
        });
    }

    btnSaveSettings.addEventListener("click", () => {
        const key = inputApiKey.value.trim();
        const model = selectGeminiModel.value;
        localStorage.setItem("gemini_api_key", key);
        localStorage.setItem("gemini_model", model);
        updateApiKeyBadge(key);
        modalSettings.classList.add("hidden");
        showToast("Đã lưu cấu hình API Key thành công!", "success");
    });

    btnToggleKeyVis.addEventListener("click", () => {
        if (inputApiKey.type === "password") {
            inputApiKey.type = "text";
            btnToggleKeyVis.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
        } else {
            inputApiKey.type = "password";
            btnToggleKeyVis.innerHTML = '<i class="fa-solid fa-eye"></i>';
        }
    });

    // ----------------------------------------------------
    // MODE SELECTION
    // ----------------------------------------------------
    modeCards.forEach(card => {
        card.addEventListener("click", () => {
            modeCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            card.querySelector("input").checked = true;
        });
    });

    function getSelectedMode() {
        const checked = document.querySelector('input[name="proc_mode"]:checked');
        return checked ? checked.value : "gemini";
    }

    // ----------------------------------------------------
    // DROPZONE & FILE UPLOAD
    // ----------------------------------------------------
    dropzone.addEventListener("click", (e) => {
        if (e.target.closest("#btn-remove-file")) return;
        fileInput.click();
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    btnRemoveFile.addEventListener("click", (e) => {
        e.stopPropagation();
        resetUploadState();
    });

    function resetUploadState() {
        currentJobId = null;
        fileInput.value = "";
        dropzone.querySelector(".dropzone-content").classList.remove("hidden");
        fileInfoPreview.classList.add("hidden");
        audioPreviewContainer.classList.add("hidden");
        audioPreviewPlayer.pause();
        audioPreviewPlayer.src = "";
        btnStartProcess.disabled = true;
    }

    async function handleFileUpload(file) {
        showToast("Đang tải file âm thanh lên hệ thống...", "info");
        btnStartProcess.disabled = true;

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Tải file thất bại");
            }

            const data = await res.json();
            currentJobId = data.job_id;
            const meta = data.metadata;

            // Render file info preview
            dropzone.querySelector(".dropzone-content").classList.add("hidden");
            fileInfoPreview.classList.remove("hidden");
            fileNameEl.textContent = data.filename;
            fileSizeEl.textContent = `${meta.size_mb} MB`;
            fileDurationEl.textContent = meta.duration_formatted;
            fileFormatEl.textContent = `${meta.format_name.toUpperCase()} • ${meta.channels}ch`;

            // Load preview audio
            audioPreviewPlayer.src = `/api/audio/${currentJobId}`;
            audioPreviewContainer.classList.remove("hidden");

            btnStartProcess.disabled = false;
            showToast("Tải file thành công! Bạn có thể bắt đầu xử lý.", "success");

        } catch (e) {
            showToast(e.message, "error");
            resetUploadState();
        }
    }

    // ----------------------------------------------------
    // PROCESS EXECUTION & PROGRESS TRACKING
    // ----------------------------------------------------
    btnStartProcess.addEventListener("click", async () => {
        if (!currentJobId) return;

        const mode = getSelectedMode();
        const apiKey = localStorage.getItem("gemini_api_key") || "";
        const geminiModel = localStorage.getItem("gemini_model") || "gemini-3.5-flash";

        if (mode === "gemini" && (!apiKey || apiKey.length < 10)) {
            modalSettings.classList.remove("hidden");
            showToast("Vui lòng cấu hình Gemini API Key trước khi bắt đầu!", "error");
            return;
        }

        // Switch to progress view
        setupSection.classList.add("hidden");
        progressSection.classList.remove("hidden");
        resultsSection.classList.add("hidden");

        processStartTime = Date.now();
        startTimer();

        // Submit process request
        const modelToUse = (mode === "gemini") ? geminiModel : "small";
        const formData = new FormData();
        formData.append("job_id", currentJobId);
        formData.append("mode", mode);
        formData.append("api_key", apiKey);
        formData.append("model_name", modelToUse);

        const speakersCount = inputSpeakersCount.value;
        if (speakersCount) formData.append("expected_speakers", speakersCount);

        const hints = inputSpeakerHints.value.trim();
        if (hints) formData.append("speaker_hints", hints);

        const ctx = inputMeetingContext.value.trim();
        if (ctx) formData.append("meeting_context", ctx);

        try {
            const res = await fetch("/api/process", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Không thể khởi chạy tiến trình");
            }

            // Start polling
            pollJobStatus(currentJobId);

        } catch (e) {
            showToast(e.message, "error");
            stopTimer();
            setupSection.classList.remove("hidden");
            progressSection.classList.add("hidden");
        }
    });

    let timerInterval = null;
    function startTimer() {
        timerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - processStartTime) / 1000);
            const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
            const s = String(elapsed % 60).padStart(2, "0");
            timerDisplay.textContent = `${m}:${s}`;
        }, 1000);
    }
    function stopTimer() {
        if (timerInterval) clearInterval(timerInterval);
    }

    function pollJobStatus(jobId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/job/${jobId}`);
                if (!res.ok) return;

                const job = await res.json();
                updateProgressUI(job);

                if (job.status === "completed") {
                    clearInterval(pollInterval);
                    stopTimer();
                    jobData = job.result;
                    renderResults(job);
                } else if (job.status === "failed") {
                    clearInterval(pollInterval);
                    stopTimer();
                    showToast(job.message || "Xử lý thất bại", "error");
                    progressMessage.textContent = "Đã xảy ra lỗi trong quá trình xử lý";
                    progressSub.innerHTML = `
                        <div style="color: #f43f5e; margin-bottom: 14px; font-weight: 500;">${escapeHtml(job.message)}</div>
                        <button id="btn-error-back" class="btn btn-glass" style="font-size: 13px;">
                            <i class="fa-solid fa-arrow-left"></i> Quay lại kiểm tra cài đặt
                        </button>
                    `;
                    document.getElementById("btn-error-back")?.addEventListener("click", () => {
                        progressSection.classList.add("hidden");
                        setupSection.classList.remove("hidden");
                    });
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 1500);
    }

    function updateProgressUI(job) {
        const pct = job.progress || 10;
        progressBarFill.style.width = `${pct}%`;
        progressPct.textContent = `${pct}%`;
        if (job.message) progressMessage.textContent = job.message;

        if (pct < 30) {
            step1.classList.add("active");
            line1.classList.remove("active");
            step2.classList.remove("active");
            line2.classList.remove("active");
            step3.classList.remove("active");
            progressSub.textContent = "Đang nạp và tối ưu hóa file ghi âm trên máy chủ";
        } else if (pct < 75) {
            step1.classList.add("active");
            line1.classList.add("active");
            step2.classList.add("active");
            line2.classList.remove("active");
            step3.classList.remove("active");
            progressSub.textContent = "AI đang lắng nghe từng đoạn, phân biệt giọng nói và gỡ băng";
        } else {
            step1.classList.add("active");
            line1.classList.add("active");
            step2.classList.add("active");
            line2.classList.add("active");
            step3.classList.add("active");
            progressSub.textContent = "Đang trích xuất quyết định, action items và tóm tắt điều hành";
        }
    }

    // ----------------------------------------------------
    // RESULTS RENDERING
    // ----------------------------------------------------
    function renderResults(job) {
        progressSection.classList.add("hidden");
        resultsSection.classList.remove("hidden");

        const res = job.result;
        const summary = res.summary || {};
        const transcript = res.transcript || [];
        const speakers = res.speakers || [];
        const meta = job.metadata || {};

        // Title and Chips
        resultMeetingTitle.textContent = summary.title || "Biên Bản Cuộc Trò Chuyện";
        resDuration.textContent = meta.duration_formatted || "01:00:00";
        resSpeakersCount.textContent = `${speakers.length} người nói`;
        resTurnsCount.textContent = `${transcript.length} lượt đối thoại`;
        tabTranscriptCount.textContent = transcript.length;

        // Initialize Audio Player
        mainAudioPlayer.src = `/api/audio/${job.job_id}`;
        setupAudioPlayer();

        // 1. Tab Summary
        renderSummaryTab(summary, speakers);

        // 2. Tab Transcript
        renderSpeakerFilters(speakers);
        renderTranscriptList(transcript);

        // 3. Tab Chat Reset
        chatMessages.innerHTML = "";
        appendChatMessage("ai", `Xin chào! Tôi đã nắm trọn vẹn nội dung cuộc họp "${summary.title}". Bạn có thể hỏi tôi bất kỳ điều gì, từ tóm tắt chi tiết, việc cần làm, hoặc ai đã phát biểu vấn đề gì!`);

        showToast("Đã hoàn tất nhận diện và tóm tắt xuất sắc!", "success");
    }

    function renderSummaryTab(summary, speakers) {
        // Overview
        sumOverview.textContent = summary.overview || "Không có tổng quan.";

        // Tags
        sumTagsContainer.innerHTML = "";
        (summary.tags || []).forEach(t => {
            const span = document.createElement("span");
            span.className = "tag-pill";
            span.textContent = `# ${t}`;
            sumTagsContainer.appendChild(span);
        });

        // Decisions
        sumDecisionsList.innerHTML = "";
        const decisions = summary.decisions || [];
        if (decisions.length === 0) {
            sumDecisionsList.innerHTML = "<li>Chưa ghi nhận quyết định cụ thể nào.</li>";
        } else {
            decisions.forEach(d => {
                const li = document.createElement("li");
                li.textContent = d;
                sumDecisionsList.appendChild(li);
            });
        }

        // Action Items
        sumActionsBody.innerHTML = "";
        const actions = summary.action_items || [];
        if (actions.length === 0) {
            sumActionsBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#94a3b8;">Không có việc cần làm được phân công</td></tr>';
        } else {
            actions.forEach(act => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong style="color: #818cf8;">${escapeHtml(act.assignee || "-")}</strong></td>
                    <td>${escapeHtml(act.task || "-")}</td>
                    <td><span class="pill-info" style="color: #f59e0b;">${escapeHtml(act.deadline || "-")}</span></td>
                `;
                sumActionsBody.appendChild(tr);
            });
        }

        // Speaker Viewpoints
        sumSpeakersViewpoints.innerHTML = "";
        const viewpoints = summary.speaker_viewpoints || [];
        viewpoints.forEach(vp => {
            const box = document.createElement("div");
            box.className = "viewpoint-box";

            // Find matching color
            const spkObj = (speakers || []).find(s => s.name === vp.speaker) || {};
            const color = spkObj.color || "#6366f1";
            const initial = (vp.speaker || "N")[0].toUpperCase();

            let stmtsHtml = "";
            (vp.key_statements || []).forEach(st => {
                stmtsHtml += `<li>${escapeHtml(st)}</li>`;
            });

            box.innerHTML = `
                <div class="viewpoint-header">
                    <div class="speaker-avatar-circle" style="background: ${color};">${initial}</div>
                    <div>
                        <div class="viewpoint-name" style="color: ${color};">${escapeHtml(vp.speaker)}</div>
                        <div class="viewpoint-role">${escapeHtml(vp.role_or_perspective || "Người tham gia")}</div>
                    </div>
                </div>
                <ul class="viewpoint-statements">
                    ${stmtsHtml}
                </ul>
            `;
            sumSpeakersViewpoints.appendChild(box);
        });

        // Key Topics
        sumTopicsContainer.innerHTML = "";
        const topics = summary.key_topics || [];
        topics.forEach(tp => {
            const div = document.createElement("div");
            div.className = "topic-item";
            div.innerHTML = `
                <div class="topic-title"><i class="fa-solid fa-angle-right" style="color: var(--accent-primary);"></i> ${escapeHtml(tp.topic)}</div>
                <div class="topic-desc">${escapeHtml(tp.discussion)}</div>
                ${tp.outcome ? `<div class="topic-outcome"><i class="fa-solid fa-circle-check"></i> ${escapeHtml(tp.outcome)}</div>` : ""}
            `;
            sumTopicsContainer.appendChild(div);
        });
    }

    function renderSpeakerFilters(speakers) {
        speakerFilterPills.innerHTML = "";
        const allBtn = document.createElement("button");
        allBtn.className = "pill active";
        allBtn.dataset.speaker = "all";
        allBtn.textContent = "Tất cả";
        allBtn.addEventListener("click", () => applySpeakerFilter("all"));
        speakerFilterPills.appendChild(allBtn);

        speakers.forEach(spk => {
            const btn = document.createElement("button");
            btn.className = "pill";
            btn.dataset.speaker = spk.name;
            btn.style.borderColor = spk.color;
            btn.innerHTML = `<span style="color:${spk.color};">●</span> ${escapeHtml(spk.name)}`;
            btn.addEventListener("click", () => applySpeakerFilter(spk.name));
            speakerFilterPills.appendChild(btn);
        });
    }

    function applySpeakerFilter(speaker) {
        activeFilterSpeaker = speaker;
        document.querySelectorAll("#speaker-filter-pills .pill").forEach(p => {
            p.classList.toggle("active", p.dataset.speaker === speaker);
        });
        filterAndRenderTranscript();
    }

    function renderTranscriptList(transcript) {
        transcriptFeed.innerHTML = "";
        const speakers = (jobData && jobData.speakers) ? jobData.speakers : [];

        transcript.forEach((seg, idx) => {
            const spkObj = speakers.find(s => s.name === seg.speaker) || {};
            const color = spkObj.color || "#6366f1";

            const div = document.createElement("div");
            div.className = "transcript-segment";
            div.dataset.index = idx;
            div.dataset.speaker = seg.speaker;
            div.dataset.start = seg.start;
            div.dataset.end = seg.end;

            div.innerHTML = `
                <div class="speaker-badge-col">
                    <button class="speaker-tag-btn" style="color: ${color};" title="Nhấp để đổi tên người nói">
                        <i class="fa-solid fa-user-pen" style="font-size: 11px;"></i>
                        <span>${escapeHtml(seg.speaker)}</span>
                    </button>
                    <button class="time-stamp-btn" title="Phát từ mốc này">
                        <i class="fa-regular fa-circle-play"></i> ${escapeHtml(seg.start)}
                    </button>
                </div>
                <div class="segment-text-col">
                    <div class="segment-text">${highlightSearchText(escapeHtml(seg.text), activeSearchTerm)}</div>
                </div>
                <div class="segment-actions">
                    <button class="btn-icon btn-copy-seg" title="Sao chép đoạn thoại">
                        <i class="fa-regular fa-copy"></i>
                    </button>
                </div>
            `;

            // Click timestamp to seek & play
            div.querySelector(".time-stamp-btn").addEventListener("click", (e) => {
                e.stopPropagation();
                seekAudioTo(seg.start);
            });

            // Click entire segment row to seek
            div.addEventListener("click", () => {
                seekAudioTo(seg.start);
            });

            // Click speaker name to rename
            div.querySelector(".speaker-tag-btn").addEventListener("click", (e) => {
                e.stopPropagation();
                openRenameModal(seg.speaker);
            });

            // Copy text
            div.querySelector(".btn-copy-seg").addEventListener("click", (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(`[${seg.start}] ${seg.speaker}: ${seg.text}`);
                showToast("Đã sao chép đoạn thoại vào clipboard", "success");
            });

            transcriptFeed.appendChild(div);
        });
    }

    function filterAndRenderTranscript() {
        if (!jobData || !jobData.transcript) return;
        const items = transcriptFeed.querySelectorAll(".transcript-segment");

        items.forEach(el => {
            const spk = el.dataset.speaker;
            const text = el.querySelector(".segment-text").textContent.toLowerCase();
            const matchesSpeaker = (activeFilterSpeaker === "all" || spk === activeFilterSpeaker);
            const matchesSearch = (!activeSearchTerm || text.includes(activeSearchTerm.toLowerCase()));

            if (matchesSpeaker && matchesSearch) {
                el.classList.remove("hidden");
                // Update highlight
                el.querySelector(".segment-text").innerHTML = highlightSearchText(escapeHtml(el.querySelector(".segment-text").textContent), activeSearchTerm);
            } else {
                el.classList.add("hidden");
            }
        });
    }

    function highlightSearchText(text, query) {
        if (!query) return text;
        const re = new RegExp(`(${query})`, "gi");
        return text.replace(re, '<mark style="background: rgba(245, 158, 11, 0.4); color: #fff; padding: 2px 4px; border-radius: 3px;">$1</mark>');
    }

    transcriptSearch.addEventListener("input", (e) => {
        activeSearchTerm = e.target.value.trim();
        btnClearSearch.classList.toggle("hidden", !activeSearchTerm);
        filterAndRenderTranscript();
    });

    btnClearSearch.addEventListener("click", () => {
        transcriptSearch.value = "";
        activeSearchTerm = "";
        btnClearSearch.classList.add("hidden");
        filterAndRenderTranscript();
    });

    // ----------------------------------------------------
    // INLINE SPEAKER RENAMING
    // ----------------------------------------------------
    function openRenameModal(oldName) {
        renamingOldName = oldName;
        renameOldName.value = oldName;
        renameNewName.value = "";
        modalRename.classList.remove("hidden");
        setTimeout(() => renameNewName.focus(), 100);
    }

    btnCloseRenameModal.addEventListener("click", () => modalRename.classList.add("hidden"));
    btnCancelRename.addEventListener("click", () => modalRename.classList.add("hidden"));

    btnConfirmRename.addEventListener("click", async () => {
        const newName = renameNewName.value.trim();
        if (!newName) {
            showToast("Vui lòng nhập tên mới cho người nói", "error");
            return;
        }

        try {
            const res = await fetch("/api/rename-speaker", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    job_id: currentJobId,
                    old_name: renamingOldName,
                    new_name: newName
                })
            });

            if (!res.ok) throw new Error("Đổi tên thất bại");
            const data = await res.json();
            jobData = data.result;

            modalRename.classList.add("hidden");
            showToast(`Đã đổi "${renamingOldName}" thành "${newName}" trên toàn bộ tài liệu!`, "success");

            // Re-render
            renderSummaryTab(jobData.summary, jobData.speakers);
            renderSpeakerFilters(jobData.speakers);
            renderTranscriptList(jobData.transcript);

        } catch (e) {
            showToast(e.message, "error");
        }
    });

    // ----------------------------------------------------
    // SYNCHRONIZED AUDIO PLAYER
    // ----------------------------------------------------
    function setupAudioPlayer() {
        mainAudioPlayer.addEventListener("timeupdate", onAudioTimeUpdate);
        mainAudioPlayer.addEventListener("loadedmetadata", () => {
            playerTotalTime.textContent = formatSec(mainAudioPlayer.duration);
        });

        btnPlayerPlay.addEventListener("click", () => {
            if (mainAudioPlayer.paused) {
                mainAudioPlayer.play();
                btnPlayerPlay.innerHTML = '<i class="fa-solid fa-pause"></i>';
            } else {
                mainAudioPlayer.pause();
                btnPlayerPlay.innerHTML = '<i class="fa-solid fa-play"></i>';
            }
        });

        playerScrubber.addEventListener("input", () => {
            const seekTo = (playerScrubber.value / 100) * mainAudioPlayer.duration;
            mainAudioPlayer.currentTime = seekTo;
        });

        // Speed Cycling: 1.0 -> 1.25 -> 1.5 -> 2.0 -> 1.0
        const speeds = [1.0, 1.25, 1.5, 2.0];
        let speedIdx = 0;
        btnSpeed.addEventListener("click", () => {
            speedIdx = (speedIdx + 1) % speeds.length;
            const spd = speeds[speedIdx];
            mainAudioPlayer.playbackRate = spd;
            btnSpeed.textContent = `${spd.toFixed(1)}x`;
        });

        // Volume
        playerVolume.addEventListener("input", () => {
            mainAudioPlayer.volume = playerVolume.value;
        });
    }

    function onAudioTimeUpdate() {
        const cur = mainAudioPlayer.currentTime;
        const dur = mainAudioPlayer.duration || 1;

        playerCurrentTime.textContent = formatSec(cur);
        playerScrubber.value = (cur / dur) * 100;

        // Find active transcript segment
        if (jobData && jobData.transcript) {
            let activeSeg = null;
            let activeIdx = -1;

            jobData.transcript.forEach((seg, idx) => {
                const s = parseTs(seg.start);
                const e = parseTs(seg.end) || (s + 5);
                if (cur >= s && cur <= e) {
                    activeSeg = seg;
                    activeIdx = idx;
                }
            });

            // Update speaking badge
            if (activeSeg) {
                playerSpeakingBadge.classList.remove("hidden");
                speakingNowName.textContent = activeSeg.speaker;
            } else {
                playerSpeakingBadge.classList.add("hidden");
            }

            // Highlight segment row
            const rows = transcriptFeed.querySelectorAll(".transcript-segment");
            rows.forEach((r, idx) => {
                if (idx === activeIdx) {
                    r.classList.add("active-segment");
                } else {
                    r.classList.remove("active-segment");
                }
            });
        }
    }

    function seekAudioTo(timestampStr) {
        const sec = parseTs(timestampStr);
        mainAudioPlayer.currentTime = sec;
        mainAudioPlayer.play();
        btnPlayerPlay.innerHTML = '<i class="fa-solid fa-pause"></i>';
    }

    function parseTs(str) {
        if (!str) return 0;
        const parts = str.trim().split(":");
        if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseFloat(parts[2]);
        if (parts.length === 2) return parseInt(parts[0]) * 60 + parseFloat(parts[1]);
        return parseFloat(str) || 0;
    }

    function formatSec(s) {
        if (isNaN(s)) return "00:00";
        const sec = Math.floor(s);
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const rem = sec % 60;
        if (h > 0) return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
        return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
    }

    // ----------------------------------------------------
    // TABS NAVIGATION
    // ----------------------------------------------------
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const target = document.getElementById(btn.dataset.tab);
            if (target) target.classList.add("active");
        });
    });

    // ----------------------------------------------------
    // TAB 3: MEETING AI CHAT
    // ----------------------------------------------------
    quickPromptBtns.forEach(b => {
        b.addEventListener("click", () => {
            chatInput.value = b.dataset.prompt;
            sendMessage();
        });
    });

    btnSendChat.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const q = chatInput.value.trim();
        if (!q || !currentJobId) return;

        chatInput.value = "";
        appendChatMessage("user", q);

        const aiBubble = appendChatMessage("ai", "Đang tra cứu và phân tích nội dung cuộc ghi âm...");

        try {
            const apiKey = localStorage.getItem("gemini_api_key") || "";
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    job_id: currentJobId,
                    question: q,
                    api_key: apiKey
                })
            });

            if (!res.ok) throw new Error("Lỗi khi kết nối tới trợ lý AI");
            const data = await res.json();
            aiBubble.querySelector(".chat-text").textContent = data.answer;

        } catch (e) {
            aiBubble.querySelector(".chat-text").textContent = `Lỗi: ${e.message}`;
        }
    }

    function appendChatMessage(sender, text) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${sender}`;
        div.innerHTML = `
            <div class="chat-avatar"><i class="fa-solid fa-${sender === 'user' ? 'user' : 'robot'}"></i></div>
            <div class="chat-text">${escapeHtml(text)}</div>
        `;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div;
    }

    // ----------------------------------------------------
    // EXPORT DOWNLOADS
    // ----------------------------------------------------
    document.querySelectorAll(".dropdown-item[data-export]").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            if (!currentJobId) return;
            const fmt = item.dataset.export;
            window.location.href = `/api/export/${currentJobId}/${fmt}`;
            showToast(`Đang tải file .${fmt}...`, "success");
        });
    });

    btnRestart.addEventListener("click", () => {
        if (confirm("Bạn có muốn làm mới để xử lý file ghi âm khác?")) {
            mainAudioPlayer.pause();
            setupSection.classList.remove("hidden");
            progressSection.classList.add("hidden");
            resultsSection.classList.add("hidden");
            resetUploadState();
        }
    });

    // ----------------------------------------------------
    // TOAST NOTIFICATION UTILITY
    // ----------------------------------------------------
    let toastTimeout = null;
    function showToast(msg, type = "info") {
        clearTimeout(toastTimeout);
        toastEl.className = `toast ${type}`;
        toastMsgEl.textContent = msg;
        toastEl.classList.remove("hidden");

        toastTimeout = setTimeout(() => {
            toastEl.classList.add("hidden");
        }, 4000);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});
