document.addEventListener('DOMContentLoaded', () => {

    // Tab Navigation
    const navBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.id === 'modal-cancel') return;
            
            navBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(t => t.classList.add('hidden'));

            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.getElementById(target).classList.remove('hidden');

            if (target === 'history') {
                loadHistory();
            } else if (target === 'settings') {
                loadSettings();
            }
        });
    });

    // Load Settings
    async function loadSettings() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            document.getElementById('base-dir').value = data.base_dir || '';
        } catch (e) {
            console.error(e);
        }
    }

    // Save Settings
    document.getElementById('save-settings-btn').addEventListener('click', async () => {
        const val = document.getElementById('base-dir').value.trim();
        const stat = document.getElementById('settings-status');
        stat.textContent = 'Saving...';
        
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_dir: val })
            });
            stat.textContent = 'Saved successfully!';
            setTimeout(() => stat.textContent = '', 2000);
        } catch (e) {
            stat.textContent = 'Failed to save.';
        }
    });

    // Load History
    async function loadHistory() {
        const tbody = document.getElementById('history-body');
        tbody.innerHTML = '<tr><td colspan="5">Loading...</td></tr>';
        
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            
            tbody.innerHTML = '';
            if (!data.downloads || data.downloads.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No history found.</td></tr>';
                return;
            }

            data.downloads.forEach(d => {
                const tr = document.createElement('tr');
                const lastPulled = d.last_downloaded_at ? new Date(d.last_downloaded_at).toISOString().split('T')[0] : 'Never';
                const safePath = d.local_path ? d.local_path.replace(/\\/g, '\\\\') : '';
                tr.innerHTML = `
                    <td>@${d.username}</td>
                    <td><span class="platform-tag">${d.platform}</span></td>
                    <td>${lastPulled}</td>
                    <td>${d.video_count}</td>
                    <td>
                        <div class="action-btns">
                            <div class="action-btn primary" onclick="redownload('${d.profile_url}')">Re-Pull</div>
                            <div class="action-btn ghost" onclick="openFolder('${safePath}')">Open</div>
                            <div class="action-btn ghost" onclick="deleteHistoryRow(${d.id})" style="color:#ffcc00;">Delete</div>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            tbody.innerHTML = '<tr><td colspan="5">Error loading history.</td></tr>';
        }
    }

    const clearHistoryBtn = document.getElementById('clear-history-btn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to completely wipe your download history?\\n\\n(Your physical media folders on disk will remain untouched.)")) return;
            try {
                const res = await fetch('/api/history', { method: 'DELETE' });
                if (res.ok) {
                    loadHistory();
                }
            } catch (e) {
                console.error('Failed to clear history:', e);
            }
        });
    }

    // Expose wrapper for history button
    window.redownload = function(url) {
        document.querySelector('[data-target="download"]').click();
        const input = document.getElementById('url-input');
        input.value = url;
        input.focus();
    };

    window.deleteHistoryRow = async function(id) {
        if (!confirm("Are you sure you want to remove this profile from your history?")) return;
        try {
            const res = await fetch('/api/history/' + id, { method: 'DELETE' });
            if (res.ok) {
                loadHistory();
            }
        } catch (e) {
            console.error("Failed to delete row:", e);
        }
    };

    window.openFolder = async function(path) {
        if (!path) return;
        try {
            await fetch('/api/open_folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
        } catch (e) {
            console.error("Failed to open folder");
        }
    };

    // Download Logic
    const pullBtn = document.getElementById('pull-btn');
    const urlInput = document.getElementById('url-input');
    const duplicateModal = document.getElementById('duplicate-modal');
    const modalCancel = document.getElementById('modal-cancel');
    const modalConfirm = document.getElementById('modal-confirm');
    let pendingUrl = '';

    pullBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;

        pullBtn.textContent = 'PULLING...';
        pullBtn.disabled = true;
        pullBtn.classList.add('inactive');
        urlInput.classList.add('active');

        try {
            const res = await fetch('/api/check_duplicate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();

            if (data.error) {
                alert(data.error);
                resetPullBtn();
                return;
            }

            document.getElementById('platform-badge').classList.remove('hidden');
            let contentStr = data.parsed.content_type === "profile" ? "Profile Detected" : "Video Detected";
            let userStr = data.parsed.username ? `· @${data.parsed.username}` : "";
            document.getElementById('platform-text').innerText = `${data.parsed.platform} · ${contentStr} ${userStr}`;

            document.getElementById('stat-platform').innerText = data.parsed.platform.toUpperCase().substring(0, 4);
            document.getElementById('stat-videos').innerText = "...";
            document.getElementById('stat-pulled').innerText = "Today";

            if (data.is_duplicate) {
                pendingUrl = url;
                let msg = '';
                const platforms = data.existing_platforms || [];
                if (platforms.includes(data.parsed.platform)) {
                    msg = `The username @${data.parsed.username} may have already been downloaded through ${data.parsed.platform}.<br><br>To update this profile's archive, click Proceed to scan for new videos.`;
                } else {
                    const existingStr = platforms.join(' and ');
                    msg = `You have already downloaded the username @${data.parsed.username} from ${existingStr}.<br><br>Do you want to scan ${data.parsed.platform} to download their videos to your archive?`;
                }
                document.getElementById('duplicate-msg').innerHTML = msg;
                duplicateModal.classList.remove('hidden');
                resetPullBtn();
            } else {
                startDownload(url);
            }
        } catch (e) {
            alert('Error connecting to server.');
            resetPullBtn();
        }
    });

    modalCancel.addEventListener('click', () => {
        duplicateModal.classList.add('hidden');
        pendingUrl = '';
    });

    modalConfirm.addEventListener('click', () => {
        duplicateModal.classList.add('hidden');
        if (pendingUrl) {
            pullBtn.textContent = 'PULLING...';
            pullBtn.disabled = true;
            pullBtn.classList.add('inactive');
            startDownload(pendingUrl);
            pendingUrl = '';
        }
    });

    function resetPullBtn() {
        pullBtn.textContent = 'PULL';
        pullBtn.disabled = false;
        pullBtn.classList.remove('inactive');
        urlInput.classList.remove('active');
    }

    let currentEventSource = null;

    async function startDownload(url) {
        urlInput.value = '';

        try {
            const res = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });
            const data = await res.json();

            if (!res.ok || data.error) {
                alert(data.error || 'Failed to start download');
                resetPullBtn();
                return;
            }

            // Sync to the single static progress container from the template
            document.getElementById('progress-container').style.opacity = '1';
            document.getElementById('prog-title').innerText = data.label;
            document.getElementById('prog-pct').innerText = '0%';
            document.getElementById('prog-fill').style.width = '0%';
            document.getElementById('prog-status').innerText = 'Connecting...';
            document.getElementById('stat-status').innerText = 'Active';
            
            // Immediately disconnect visual lockout globally permitting multiple synchronous queue injections without destroying background connection vectors.
            resetPullBtn();

            if (currentEventSource) currentEventSource.close();
            currentEventSource = new EventSource('/api/progress/' + data.task_id);
            
            currentEventSource.onmessage = function(event) {
                const state = JSON.parse(event.data);
                
                document.getElementById('prog-status').innerText = state.msg;
                document.getElementById('prog-pct').innerText = `${state.pct}%`;
                document.getElementById('prog-fill').style.width = `${state.pct}%`;
                
                if (state.total !== undefined) {
                    document.getElementById('stat-videos').innerText = state.total;
                }

                if (state.status === 'completed' || state.status === 'error') {
                    currentEventSource.close();
                    document.getElementById('stat-status').innerText = state.status === 'completed' ? 'Done' : 'Error';
                    if (state.status === 'completed') {
                        document.getElementById('prog-fill').style.background = '#FFFFFF';
                    } else {
                        document.getElementById('prog-fill').style.background = '#ff4d4d';
                    }
                }
            };

            currentEventSource.onerror = function() {
                document.getElementById('prog-status').innerText = "Connection lost.";
                document.getElementById('stat-status').innerText = 'Error';
                currentEventSource.close();
                resetPullBtn();
            };
        } catch(e) {
            alert('Error starting download.');
            resetPullBtn();
        }
    }

    // Init call
    loadSettings();
});
