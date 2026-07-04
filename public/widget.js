(function () {
    // Generate simple UUID for session context
    function generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }
    const sessionId = generateSessionId();

    // Dynamically inject stylesheet link
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    const scriptSrc = document.currentScript ? document.currentScript.src : "http://localhost:8000/widget.js";
    const baseOrigin = new URL(scriptSrc).origin;
    link.href = baseOrigin + '/widget.css';
    document.head.appendChild(link);

    // Create widget container
    const container = document.createElement('div');
    container.id = 'hackx-widget-container';

    container.innerHTML = `
        <div id="hackx-greeting-bubble">
            <div class="hackx-bubble-close">&times;</div>
            <div id="hackx-greeting-text">👋 Hi there!<br/>Need help with HackX?</div>
        </div>
                <div id="hackx-chat-panel">
            <div id="hackx-header">
                <div class="header-title">
                    <div class="header-main-title">
                        <div class="header-avatar-container">
                            <img src="${baseOrigin}/assets/mascot-with-lap.png" alt="Bot" />
                        </div>
                        <span>HackX Assistant</span>
                    </div>
                    <div class="header-status-bar">
                        <div class="hackx-online-dot"></div>
                        <span>Online</span>
                    </div>
                </div>
                <div id="hackx-close">&times;</div>
            </div>
            <div id="hackx-context-header">
                <span class="hackx-context-indicator"></span>
                <button class="hackx-switch-comp-btn">Switch Competition</button>
            </div>
            <div id="hackx-selection-screen">
                <h3>Choose your competition</h3>
                <p>Please select a category to continue</p>
                <div class="hackx-comp-btn" data-comp="hackx">
                    <span class="hackx-comp-btn-title">HackX</span>
                    <span class="hackx-comp-btn-desc">University & Open Category</span>
                </div>
                <div class="hackx-comp-btn" data-comp="hackxjr">
                    <span class="hackx-comp-btn-title">HackX Jr</span>
                    <span class="hackx-comp-btn-desc">School Category</span>
                </div>
            </div>
            <div id="hackx-messages" style="display: none;"></div>
            <div id="hackx-input-area" style="display: none;">
                <input type="text" id="hackx-input" placeholder="Type your question..." />
                <button id="hackx-send">Send</button>
            </div>
        </div>
        <div id="hackx-mascot-launcher" class="greeting">
            <img id="hackx-mascot-img" src="${baseOrigin}/assets/mascot-one-handed.png" alt="Mascot" />
        </div>
    `;

    document.body.appendChild(container);

    const mascotLauncher = document.getElementById('hackx-mascot-launcher');
    const mascotImg = document.getElementById('hackx-mascot-img');
    const greetingBubble = document.getElementById('hackx-greeting-bubble');
    const bubbleClose = greetingBubble.querySelector('.hackx-bubble-close');
    const panel = document.getElementById('hackx-chat-panel');
    const closeBtn = document.getElementById('hackx-close');
    const input = document.getElementById('hackx-input');
    const sendBtn = document.getElementById('hackx-send');
    const messages = document.getElementById('hackx-messages');

    let selectedCompetition = sessionStorage.getItem('hackx_selected_competition');
    const selectionScreen = document.getElementById('hackx-selection-screen');
    const contextHeader = document.getElementById('hackx-context-header');
    const contextIndicator = contextHeader.querySelector('.hackx-context-indicator');
    const switchCompBtn = contextHeader.querySelector('.hackx-switch-comp-btn');

    function applyCompetitionContext() {
        if (!selectedCompetition) {
            selectionScreen.style.display = 'flex';
            messages.style.display = 'none';
            input.parentElement.style.display = 'none';
            contextHeader.style.display = 'none';
            isWelcomeShown = false;
        } else {
            selectionScreen.style.display = 'none';
            messages.style.display = 'flex';
            input.parentElement.style.display = 'flex';
            contextHeader.style.display = 'flex';
            contextIndicator.textContent = '🟢 ' + (selectedCompetition === 'hackx' ? 'HackX' : 'HackX Jr');

            if (!isWelcomeShown) {
                showWelcomeMessage();
                isWelcomeShown = true;
            }
        }
    }

    document.querySelectorAll('.hackx-comp-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            selectedCompetition = e.currentTarget.getAttribute('data-comp');
            sessionStorage.setItem('hackx_selected_competition', selectedCompetition);
            applyCompetitionContext();
        });
    });

    switchCompBtn.addEventListener('click', () => {
        selectedCompetition = null;
        sessionStorage.removeItem('hackx_selected_competition');
        messages.innerHTML = ''; // clear chat history
        applyCompetitionContext();
    });


    // State definitions
    const STATES = {
        GREETING: 'greeting',
        IDLE: 'idle',
        THINKING: 'thinking',
        SUCCESS: 'success'
    };

    const mascotImages = {
        [STATES.GREETING]: baseOrigin + '/assets/mascot-one-handed.png',
        [STATES.IDLE]: baseOrigin + '/assets/mascot-one-handed.png',
        [STATES.THINKING]: baseOrigin + '/assets/mascot-with-lap.png',
        [STATES.SUCCESS]: baseOrigin + '/assets/mascot-two-handed.png'
    };

    // Debug Mode Configuration: active if URL has ?debug=true or localStorage has hackx_debug = true
    const urlParams = new URLSearchParams(window.location.search);
    const DEBUG = urlParams.has('debug') || (localStorage.getItem('hackx_debug') === 'true');

    const tierLabels = {
        0: 'GREETING',
        1: 'GUARD',
        2: 'CACHE',
        4: 'FAQ',
        5: 'VECTOR',
        6: 'LLM'
    };

    // Preload all assets to ensure lag-free state transitions
    Object.values(mascotImages).forEach(src => {
        const img = new Image();
        img.src = src;
    });
    // Preload VR mascot
    const vrMascot = new Image();
    vrMascot.src = baseOrigin + '/assets/vr-mascot.png';

    let isWelcomeShown = false;
    let currentMascotState = STATES.GREETING;
    let greetingTimeout = null;

    function setMascotState(state) {
        if (!mascotImages[state]) return;
        currentMascotState = state;
        mascotImg.src = mascotImages[state];

        mascotLauncher.className = '';
        mascotLauncher.classList.add(state);
    }

    // Initialize greeting bubble
    setTimeout(() => {
        if (currentMascotState === STATES.GREETING) {
            greetingBubble.classList.add('show');
            greetingTimeout = setTimeout(() => {
                dismissGreeting();
            }, 5000);
        }
    }, 800);

    function dismissGreeting() {
        greetingBubble.classList.remove('show');
        if (greetingTimeout) {
            clearTimeout(greetingTimeout);
            greetingTimeout = null;
        }
        if (currentMascotState === STATES.GREETING) {
            setMascotState(STATES.IDLE);
        }
    }

    bubbleClose.addEventListener('click', (e) => {
        e.stopPropagation();
        dismissGreeting();
    });

    // Toggle chat panel
    mascotLauncher.addEventListener('click', () => {
        dismissGreeting();

        if (panel.style.display === 'flex') {
            panel.style.display = 'none';
            setMascotState(STATES.IDLE);
        } else {
            panel.style.display = 'flex';
            setMascotState(STATES.THINKING);
            applyCompetitionContext();
        }
    });

    closeBtn.addEventListener('click', () => {
        panel.style.display = 'none';
        setMascotState(STATES.IDLE);
    });


    function showWelcomeMessage() {
        const wrapper = document.createElement('div');
        wrapper.className = 'hackx-msg bot';

        let actionsHtml = '';
        const actions = ['Registration', 'Eligibility', 'Timeline', 'Rules & Guidelines', 'Contact'];
        actions.forEach(action => {
            actionsHtml += `
                <div class="hackx-menu-item" data-query="${action}">
                    <span>${action}</span>
                    <span class="hackx-chevron">&rsaquo;</span>
                </div>
            `;
        });

        wrapper.innerHTML = `
            Hi there! 👋<br/>
            I'm HackX Assistant. I can help you with all things ${selectedCompetition === 'hackx' ? 'HackX' : 'HackX Jr'}.<br/><br/>
            You can ask me about:
            <div class="hackx-menu-list">
                ${actionsHtml}
            </div>
        `;
        messages.appendChild(wrapper);

        // Bind quick reply list events
        wrapper.querySelectorAll('.hackx-menu-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const target = e.currentTarget;
                const queryText = target.getAttribute('data-query');
                input.value = queryText;
                sendMessage();
            });
        });
    }

    function addMessage(text, sender, tierInfo = null, source = null) {
        // Remove any previous quick reply chip containers to avoid layout clutter
        const oldChips = messages.querySelectorAll('.hackx-browse-more-container');
        oldChips.forEach(el => el.remove());

        const msg = document.createElement('div');
        msg.className = `hackx-msg ${sender}`;

        let lines = text.split('\n');
        let htmlLines = [];
        let inList = false;

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];

            // Bold
            line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Links
            line = line.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: var(--hackx-cyan); text-decoration: underline; font-weight: 500;">$1</a>');

            let listMatch = line.trim().match(/^[-*]\s+(.*)/);
            if (listMatch) {
                if (!inList) {
                    htmlLines.push('<ul style="margin: 8px 0; padding-left: 20px;">');
                    inList = true;
                }
                htmlLines.push('<li style="margin-bottom: 4px;">' + listMatch[1] + '</li>');
            } else {
                if (inList) {
                    htmlLines.push('</ul>');
                    inList = false;
                }
                htmlLines.push(line);
            }
        }
        if (inList) {
            htmlLines.push('</ul>');
        }

        let content = htmlLines.join('<br/>');
        // Clean up <br/> tags around lists
        content = content.replace(/<br\/>\s*<ul/g, '<ul').replace(/<\/ul>\s*<br\/>/g, '</ul>');

        msg.innerHTML = content;

        // Add meta info (Debug Badge only - Source info completely removed from UI)
        if (sender === 'bot' && DEBUG && tierInfo !== null) {
            const meta = document.createElement('div');
            meta.className = 'hackx-msg-meta';

            let label = 'SYSTEM';
            if (tierInfo === 6 && source === 'retrieved_chunks') {
                label = 'FALLBACK';
            } else if (tierLabels[tierInfo]) {
                label = tierLabels[tierInfo];
            }

            meta.innerHTML = `<span></span><span class="hackx-debug-badge">⚡ ${label}</span>`;
            msg.appendChild(meta);
        }

        messages.appendChild(msg);

        // If it's a bot response, also append the browse chips at the bottom
        if (sender === 'bot') {
            const browseContainer = document.createElement('div');
            browseContainer.className = 'hackx-browse-more-container';

            browseContainer.innerHTML = `
                <div class="hackx-browse-more-text" style="margin-top: 10px; font-size: 12px; color: var(--hackx-muted); font-weight: 500;">Do you want further clarifications in other areas?</div>
                <div class="hackx-quick-replies" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px;">
                    <div class="hackx-chip" data-query="Registration">Registration</div>
                    <div class="hackx-chip" data-query="Eligibility">Eligibility</div>
                    <div class="hackx-chip" data-query="Timeline">Timeline</div>
                    <div class="hackx-chip" data-query="Rules & Guidelines">Rules & Guidelines</div>
                    <div class="hackx-chip" data-query="Contact">Contact</div>
                </div>
            `;

            messages.appendChild(browseContainer);

            // Bind click handlers to the bottom chips
            browseContainer.querySelectorAll('.hackx-chip').forEach(chip => {
                chip.addEventListener('click', (e) => {
                    const queryText = e.currentTarget.getAttribute('data-query');
                    input.value = queryText;
                    sendMessage();
                });
            });
        }

        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        const msg = document.createElement('div');
        msg.className = 'hackx-msg bot';
        msg.id = 'hackx-typing-indicator';
        msg.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return msg;
    }

    async function sendMessage() {
        const text = input.value.strip ? input.value.strip() : input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';

        const typingIndicator = showTyping();
        setMascotState(STATES.THINKING);

        try {
            const response = await fetch(baseOrigin + "/api/chat", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: sessionId, competition_id: selectedCompetition })
            });

            if (!response.ok) {
                if (response.status === 429) {
                    throw new Error("Too many requests. Please wait a moment.");
                }
                throw new Error("Server error");
            }

            const data = await response.json();
            typingIndicator.remove();
            addMessage(data.answer, 'bot', data.tier, data.source);

            // Switch to SUCCESS state for 1.5 seconds
            setMascotState(STATES.SUCCESS);
            setTimeout(() => {
                if (panel.style.display === 'flex') {
                    setMascotState(STATES.THINKING);
                } else {
                    setMascotState(STATES.IDLE);
                }
            }, 1500);

        } catch (error) {
            typingIndicator.remove();
            const errMsg = error.message.includes("Too many requests")
                ? "Too many requests. Please wait a moment."
                : "Oops! I couldn't reach the server. Please try again.";
            addMessage(errMsg, 'bot');

            if (panel.style.display === 'flex') {
                setMascotState(STATES.THINKING);
            } else {
                setMascotState(STATES.IDLE);
            }
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

})();
