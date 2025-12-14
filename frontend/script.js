
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔍 searchInput:', document.getElementById('searchInput'));
    console.log('🔍 searchBtn:', document.getElementById('searchBtn'));
});

// Theme Toggle
const themeToggle = document.getElementById('themeToggle');
let isDarkMode = false;

themeToggle.addEventListener('click', () => {
    isDarkMode = !isDarkMode;
    document.body.style.transition = 'all 0.3s ease';

    if (isDarkMode) {
        document.documentElement.style.setProperty('--bg-gradient-start', '#1a1a2e');
        document.documentElement.style.setProperty('--bg-gradient-end', '#2d1b3d');
        document.documentElement.style.setProperty('--header-bg', 'rgba(30, 30, 46, 0.8)');
        document.documentElement.style.setProperty('--text-primary', '#ffffff');
        document.documentElement.style.setProperty('--text-secondary', '#a0a0b0');
        document.documentElement.style.setProperty('--search-bg', '#2a2a3e');
    } else {
        document.documentElement.style.setProperty('--bg-gradient-start', '#d4e7f5');
        document.documentElement.style.setProperty('--bg-gradient-end', '#e8d4f5');
        document.documentElement.style.setProperty('--header-bg', 'rgba(255, 255, 255, 0.8)');
        document.documentElement.style.setProperty('--text-primary', '#1a1a1a');
        document.documentElement.style.setProperty('--text-secondary', '#6b7280');
        document.documentElement.style.setProperty('--search-bg', '#ffffff');
    }
});

// Search Functionality
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const resultsContainer = document.getElementById('resultsContainer');
const loadingIndicator = document.getElementById('loadingIndicator');

// Clicking the logo should act as "home" and clear search state
const homeLogo = document.getElementById('homeLogo');
if (homeLogo) {
    homeLogo.addEventListener('click', () => {
        // Clear search input
        if (searchInput) {
            searchInput.value = '';
        }

        // Clear results
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
            resultsContainer.style.display = 'none';
        }

        // Hide loading spinner if visible
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }

        // Remove query params from URL
        const cleanUrl = window.location.origin + window.location.pathname;
        window.history.pushState({}, '', cleanUrl);

        // Scroll back to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}


// Backend API URL - adjust if your backend runs on a different port
// Use the global API_BASE_URL defined in auth.js if available; otherwise fall back to localhost
if (typeof API_BASE_URL === 'undefined') {
    // Fallback only when no global API_BASE_URL is defined
    API_BASE_URL = 'http://localhost:8000';
}

// Utility function to escape HTML and prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Get current page number from URL
function getCurrentPageFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const pagenum = parseInt(urlParams.get('pagenum')) || 1;
    return pagenum;
}

// Update URL with page number
function updateURLWithPage(query, pageNum) {
    const url = new URL(window.location.origin + window.location.pathname);
    url.searchParams.set('forminput', query.trim());
    url.searchParams.set('pagenum', pageNum);
    window.history.pushState({}, '', url.toString());
}

async function performSearch(query, pageNum = 1) {
    if (!query || !query.trim()) {
        searchInput.focus();
        return;
    }

    // Update URL
    updateURLWithPage(query, pageNum);

    // Show loading state
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
        resultsContainer.style.display = 'none';
    }

    try {
        // Use URLSearchParams to properly encode the query parameter
        const url = new URL(`${API_BASE_URL}/search`);
        url.searchParams.set('forminput', query.trim());
        url.searchParams.set('pagenum', pageNum);
        const response = await fetch(url.toString());

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Hide loading indicator
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }

        // Display results
        if (resultsContainer && data.results && data.results.length > 0) {
            displayResults(
                data.results,
                data.query,
                data.pagination,
                data.current_page,
                data.results_count_text
            );
            resultsContainer.style.display = 'block';

            // Scroll to results
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (resultsContainer) {
            resultsContainer.innerHTML = '<div class="no-results">No results found. Please try a different search query.</div>';
            resultsContainer.style.display = 'block';
        }
    } catch (error) {
        console.error('Search error:', error);

        // Hide loading indicator
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }

        // Show error message
        if (resultsContainer) {
            resultsContainer.innerHTML = `<div class="error-message">Error: ${error.message}. Please make sure the backend server is running on ${API_BASE_URL}</div>`;
            resultsContainer.style.display = 'block';
        }
    }
}

function displayResults(results, query, pagination, currentPage, resultsCountText) {
    // Clean up the query display - replace + with spaces
    const displayQuery = query.replace(/\+/g, ' ');

    // Build pagination HTML
    const paginationHTML = buildPaginationHTML(pagination, currentPage, displayQuery);

    // Show simple format: "Found 10 results in page 1"
    const pageNumber = currentPage || 1;
    const resultCount = results.length;
    const displayCountText = `Found ${resultCount} result${resultCount !== 1 ? 's' : ''} in page ${pageNumber}`;

    const resultsHTML = `
        <div class="results-header">
            <h2>Search Results for "${displayQuery}"</h2>
            <p class="results-count">${displayCountText}</p>
        </div>
        <div class="results-list">
            ${results.map((result, index) => {
                // Clean up title - remove extra spaces and fix formatting
                const cleanTitle = (result.title || 'Untitled')
                    .replace(/\s+/g, ' ')
                    .trim();

                // Process headline HTML - extract text and preserve bold tags
                let headlineHTML = result.headline || '';

                // Extract doc_id if available
                const docId = result.doc_id || '';
                const currentQuery = query.replace(/\+/g, ' ');

                return `
                <div class="result-card" data-doc-url="${result.title_link || result.full_doc_link || '#'}" data-doc-title="${cleanTitle}" data-doc-id="${docId}" data-query="${currentQuery}">
                    <div class="result-title">
                        <a href="${result.title_link || '#'}" target="_blank" rel="noopener noreferrer" class="title-link">
                            ${cleanTitle}
                        </a>
                        <button class="summarize-btn" data-index="${index}" title="Get AI Summary">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                                <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                            </svg>
                            <span>AI Summary</span>
                        </button>
                        <button class="chat-about-btn" data-index="${index}" title="Chat about this case">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                            </svg>
                            <span>Chat</span>
                        </button>
                    </div>
                    ${headlineHTML ? `
                    <div class="result-headline">
                        ${headlineHTML}
                    </div>
                    ` : ''}
                    <div class="result-meta">
                        ${result.doc_source ? `<span class="doc-source">${result.doc_source}</span>` : ''}
                        ${result.cites ? `<a href="#" class="meta-link">${result.cites}</a>` : ''}
                        ${result.cited_by ? `<a href="#" class="meta-link">${result.cited_by}</a>` : ''}
                        ${result.author ? `<a href="#" class="meta-link">${result.author}</a>` : ''}
                        ${result.full_doc_link ? `<a href="${result.full_doc_link}" target="_blank" class="meta-link full-doc">Full Document</a>` : ''}
                    </div>
                </div>
                `;
            }).join('')}
        </div>
        ${paginationHTML}
    `;

    resultsContainer.innerHTML = resultsHTML;

    // Attach pagination event listeners
    attachPaginationListeners(displayQuery);

    // Attach summarize button listeners
    attachSummarizeListeners();

    // Attach chat button listeners
    attachChatListeners();
}

function attachSummarizeListeners() {
    const summarizeButtons = document.querySelectorAll('.summarize-btn');
    summarizeButtons.forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            const resultCard = button.closest('.result-card');
            const docUrl = resultCard.getAttribute('data-doc-url');
            const docTitle = resultCard.getAttribute('data-doc-title');
            const docId = resultCard.getAttribute('data-doc-id');
            const query = resultCard.getAttribute('data-query');

            // Prefer doc_id if available (more reliable)
            if (!docId && (!docUrl || docUrl === '#')) {
                alert('Document information not available');
                return;
            }

            // Show summary modal
            showSummaryModal(docUrl, docTitle, docId, query);
        });
    });
}

function attachChatListeners() {
    const chatButtons = document.querySelectorAll('.chat-about-btn');
    chatButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const resultCard = button.closest('.result-card');
            const docId = resultCard.getAttribute('data-doc-id');
            const docTitle = resultCard.getAttribute('data-doc-title');
            const query = resultCard.getAttribute('data-query');

            // Prefer doc_id if available (more reliable)
            if (!docId) {
                showNotification('Document information not available for chat', 'error');
                return;
            }

            // Check if chat API is available
            if (window.ChatAPI && window.ChatAPI.startChatWithCase) {
                window.ChatAPI.startChatWithCase(docId, query, docTitle);
            } else {
                showNotification('Chat functionality not available', 'error');
            }
        });
    });
}

async function showSummaryModal(docUrl, docTitle, docId = null, query = '') {
    // Check if user is authenticated
    if (!isAuthenticated()) {
        // Show login prompt
        showNotification('Please login or sign up to view AI summaries', 'error');
        openModal('loginModal');
        return;
    }

    // Create modal if it doesn't exist
    let modal = document.getElementById('summaryModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'summaryModal';
        modal.className = 'summary-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>AI Summary</h2>
                    <button class="close-btn" id="closeModal">&times;</button>
                </div>
                <div class="modal-body" id="modalBody">
                    <div class="loading-summary">
                        <div class="spinner-small"></div>
                        <p>Fetching document and generating summaries...</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Close button handler
        document.getElementById('closeModal').addEventListener('click', () => {
            modal.style.display = 'none';
        });

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    // Show modal
    modal.style.display = 'flex';
    const modalBody = document.getElementById('modalBody');
    modalBody.innerHTML = `
        <div class="loading-summary">
            <div class="spinner-small"></div>
            <p>Fetching document and generating summaries...</p>
        </div>
    `;

    try {
        // Call summarize API - prefer doc_id if available
        const url = new URL(`${API_BASE_URL}/summarize`);
        if (docId) {
            url.searchParams.set('doc_id', docId);
            url.searchParams.set('query', query);
        } else {
            url.searchParams.set('document_url', docUrl);
        }
        url.searchParams.set('title', docTitle);

        // Add authentication header
        const headers = {
            'Authorization': `Bearer ${getAuthToken()}`
        };

        const response = await fetch(url.toString(), { headers });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Display summary for the logged-in user's role
        const user = (typeof getCurrentUser === 'function') ? getCurrentUser() : null;
        const isLawyer = !!(user && user.user_type === 'lawyer');
        modalBody.innerHTML = `
            <div class="summary-container">
                <div class="summary-header">
                    <h3>${docTitle}</h3>
                    <a href="${docUrl}" target="_blank" class="view-original">View Original Document →</a>
                </div>

                <div class="ai-warning">
                    <span class="warning-icon">⚠️</span>
                    <span>This summary is AI-generated. Please consult a qualified lawyer before relying on it.</span>
                </div>

                <div class="summary-content">
                    <h4>${isLawyer ? '⚖️ Professional Legal Analysis' : '👤 Citizen-Friendly Summary'}</h4>
                    <div class="summary-text">${escapeHtml((isLawyer ? data.lawyer_summary : data.citizen_summary) || 'Summary not available')}</div>
                </div>
            </div>
        `;

    } catch (error) {
        console.error('Summary error:', error);
        modalBody.innerHTML = `
            <div class="error-message">
                <p>❌ Error generating summary: ${error.message}</p>
                <p>Please try again later or check if the document URL is accessible.</p>
            </div>
        `;
    }
}

function buildPaginationHTML(pagination, currentPage, query) {
    if (!pagination || pagination.total_pages <= 1) {
        return '';
    }

    const totalPages = pagination.total_pages || 1;
    const hasPrevious = currentPage > 1;
    const hasNext = currentPage < totalPages;

    // Build page number buttons
    let pageButtons = '';

    // Previous button (only show if not on first page)
    if (hasPrevious) {
        pageButtons += `
            <a href="#" class="pagination-link" data-page="${currentPage - 1}" data-action="prev">
                Previous
            </a>
        `;
    }

    // Generate page numbers to show (always 10 numbers)
    const pagesToShow = generatePageNumbers(currentPage, totalPages, []);

    pagesToShow.forEach(pageNum => {
        const isActive = pageNum === currentPage;
        pageButtons += `
            <a href="#" class="pagination-link ${isActive ? 'active' : ''}" data-page="${pageNum}">
                ${pageNum}
            </a>
        `;
    });

    // Next button (only show if not on last page)
    if (hasNext) {
        pageButtons += `
            <a href="#" class="pagination-link" data-page="${currentPage + 1}" data-action="next">
                Next
            </a>
        `;
    }

    return `
        <div class="pagination-container">
            ${pageButtons}
        </div>
    `;
}

function generatePageNumbers(currentPage, totalPages, availablePages) {
    const pages = [];
    const maxVisible = 10; // Always show 10 page numbers

    if (totalPages <= maxVisible) {
        // Show all pages if total is 10 or less
        for (let i = 1; i <= totalPages; i++) {
            pages.push(i);
        }
    } else {
        // Calculate the range to show (always 10 pages)
        let start, end;

        // If we're in the first 5 pages, show 1-10
        if (currentPage <= 5) {
            start = 1;
            end = 10;
        }
        // If we're in the last 5 pages, show the last 10 pages
        else if (currentPage >= totalPages - 4) {
            start = totalPages - 9;
            end = totalPages;
        }
        // Otherwise, center around current page
        else {
            // Center the current page: show 5 pages before and 4 after (or vice versa)
            start = currentPage - 4;
            end = currentPage + 5;
        }

        // Generate the page numbers
        for (let i = start; i <= end; i++) {
            pages.push(i);
        }
    }

    return pages;
}

function attachPaginationListeners(query) {
    const paginationLinks = document.querySelectorAll('.pagination-link:not(.disabled)');

    paginationLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageNum = parseInt(link.getAttribute('data-page'));
            if (pageNum && pageNum >= 1) {
                performSearch(query, pageNum);
            }
        });
    });
}

searchBtn.addEventListener('click', () => {
    console.log('🔍 Search button clicked!');
    const query = searchInput.value.trim();
    console.log('📝 Query:', query);
    if (!query) {
        console.log('❌ Empty query');
        searchInput.focus();
        return;
    }
    console.log('🚀 Starting search...');
    performSearch(query, 1); // Always start from page 1 for new searches
});

searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        searchBtn.click();
    }
});

// Check URL on page load for pagination
window.addEventListener('load', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const forminput = urlParams.get('forminput');
    const pagenum = parseInt(urlParams.get('pagenum')) || 1;

    if (forminput) {
        // Restore search from URL
        const query = forminput.replace(/\+/g, ' ');
        searchInput.value = query;
        performSearch(query, pagenum);
    }
});

// Voice Search
const voiceBtn = document.getElementById('voiceBtn');
const voiceIcon = voiceBtn.querySelector('.voice-icon');
const stopIcon = voiceBtn.querySelector('.stop-icon');
let isListening = false;
let recognition = null;
let manuallyStopped = false;
let capturedSegments = [];
let interimSegment = '';

const resetVoiceUI = () => {
    isListening = false;
    voiceIcon.style.display = 'block';
    stopIcon.style.display = 'none';
    voiceBtn.style.color = '';
};

voiceBtn.addEventListener('click', () => {
    const supportsSpeech =
        'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;

    if (!supportsSpeech) {
        alert('Voice recognition is not supported in your browser. Please try Chrome or Edge.');
        return;
    }

    if (!isListening) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();

        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;

        manuallyStopped = false;
        capturedSegments = [];
        interimSegment = '';
        recognition.start();
        isListening = true;

        voiceIcon.style.display = 'none';
        stopIcon.style.display = 'block';
        voiceBtn.style.color = '#ef4444';

        recognition.onresult = (event) => {
            interimSegment = '';
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const result = event.results[i];
                const transcript = result[0].transcript.trim();
                if (transcript.length === 0) {
                    continue;
                }

                if (result.isFinal) {
                    capturedSegments.push(transcript);
                } else {
                    interimSegment = transcript;
                }
            }

            const combined = [...capturedSegments];
            if (interimSegment) {
                combined.push(interimSegment);
            }
            searchInput.value = combined.join(' ').replace(/\s+/g, ' ').trim();
        };

        recognition.onerror = () => {
            manuallyStopped = true;
            resetVoiceUI();
            if (recognition) {
                recognition.stop();
            }
            recognition = null;
            alert('Voice recognition error. Please try again.');
        };

        recognition.onend = () => {
            if (!manuallyStopped && recognition) {
                try {
                    recognition.start();
                } catch (error) {
                    manuallyStopped = true;
                    resetVoiceUI();
                    recognition = null;
                    console.error('Failed to restart speech recognition:', error);
                }
            } else {
                resetVoiceUI();
                recognition = null;
                manuallyStopped = false;
                capturedSegments = [];
                interimSegment = '';
            }
        };
    } else {
        manuallyStopped = true;
        capturedSegments = [];
        interimSegment = '';
        resetVoiceUI();
        if (recognition) {
            recognition.stop();
        }
    }
});

// Search Input Focus Effect
searchInput.addEventListener('focus', () => {
    searchInput.parentElement.style.transform = 'translateY(-2px)';
});

searchInput.addEventListener('blur', () => {
    searchInput.parentElement.style.transform = 'translateY(0)';
});

// Login Button
const loginBtn = document.querySelector('.login-btn');
loginBtn.addEventListener('click', () => {
    // Open the actual login modal instead of demo alert
    const loginModal = document.getElementById('loginModal');
    if (loginModal) {
        loginModal.style.display = 'block';
    }
});

// Add smooth scroll behavior
document.documentElement.style.scrollBehavior = 'smooth';

// Console welcome message
console.log('%cIndian Kanoon Legal App', 'font-size: 20px; font-weight: bold; color: #4f46e5;');
console.log('Features: Theme Toggle, Voice Search, Multi-language Support');

// Text scale controls with limited interactions
const rootElement = document.documentElement;
const textScaleButtons = document.querySelectorAll('.text-scale-btn');
const scaleDownBtn = document.getElementById('textScaleDown');
const scaleDefaultBtn = document.getElementById('textScaleDefault');
const scaleUpBtn = document.getElementById('textScaleUp');

const SCALE_STEP = 0.1;
const MIN_SCALE = 0.7;
const MAX_SCALE = 1.3;
const MAX_CLICKS_PER_DIRECTION = 3;

const scaleState = {
    currentScale: 1,
    decreaseClicks: 0,
    increaseClicks: 0,
    defaultUsed: false,
};

const applyTextScale = (scale) => {
    const clamped = Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
    scaleState.currentScale = Number(clamped.toFixed(2));
    rootElement.style.setProperty('--font-scale', scaleState.currentScale);
};

const setActiveButton = (button) => {
    textScaleButtons.forEach((btn) => btn.classList.remove('active'));
    button.classList.add('active');
};

const updateButtonStates = () => {
    scaleDownBtn.disabled = scaleState.decreaseClicks >= MAX_CLICKS_PER_DIRECTION;
    scaleUpBtn.disabled = scaleState.increaseClicks >= MAX_CLICKS_PER_DIRECTION;
    scaleDefaultBtn.disabled = scaleState.defaultUsed;
};

applyTextScale(scaleState.currentScale);
setActiveButton(scaleDefaultBtn);
updateButtonStates();

scaleDownBtn.addEventListener('click', () => {
    if (scaleState.decreaseClicks >= MAX_CLICKS_PER_DIRECTION) {
        return;
    }

    scaleState.decreaseClicks += 1;
    scaleState.defaultUsed = false;
    applyTextScale(scaleState.currentScale - SCALE_STEP);
    setActiveButton(scaleDownBtn);
    updateButtonStates();
});

scaleUpBtn.addEventListener('click', () => {
    if (scaleState.increaseClicks >= MAX_CLICKS_PER_DIRECTION) {
        return;
    }

    scaleState.increaseClicks += 1;
    scaleState.defaultUsed = false;
    applyTextScale(scaleState.currentScale + SCALE_STEP);
    setActiveButton(scaleUpBtn);
    updateButtonStates();
});

scaleDefaultBtn.addEventListener('click', () => {
    if (scaleState.defaultUsed) {
        return;
    }

    scaleState.defaultUsed = true;
    scaleState.decreaseClicks = 0;
    scaleState.increaseClicks = 0;
    applyTextScale(1);
    setActiveButton(scaleDefaultBtn);
    updateButtonStates();
});




