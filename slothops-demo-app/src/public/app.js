const consoleEl = document.getElementById('console');

function log(msg, type = 'info') {
    const div = document.createElement('div');
    const time = new Date().toLocaleTimeString();
    
    if (type === 'error') {
        div.className = 'text-red-500 font-bold';
        div.innerText = `[${time}] ERR: ${msg}`;
    } else if (type === 'success') {
        div.className = 'text-green-400';
        div.innerText = `[${time}] OK: ${msg}`;
    } else {
        div.className = 'text-gray-400';
        div.innerText = `[${time}] INF: ${msg}`;
    }

    consoleEl.appendChild(div);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

async function triggerBug(path) {
    log(`Sending GET request to ${path}...`);
    try {
        const res = await fetch(path);
        const text = await res.text();
        
        if (res.ok) {
            log(text, 'success');
        } else {
            // Usually Express default error handler sends HTML on crash, or our JSON
            try {
                const json = JSON.parse(text);
                log(`HTTP ${res.status}: ${JSON.stringify(json)}`, 'error');
            } catch (e) {
                // Sentry catches it on the backend, but Express dumps the stack to the frontend
                const firstLine = text.split('\n')[0].replace(/<[^>]*>?/gm, ''); // pull the Error type from HTML dump
                log(`Server crashed! 💥 Sentry Webhook should fire immediately. [${firstLine.substring(0, 80)}...]`, 'error');
            }
        }
    } catch (e) {
        log(`Network failed: ${e.message}`, 'error');
    }
}

async function triggerPost(path, body = {}) {
    log(`Sending POST request to ${path}...`);
    try {
        const res = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const text = await res.text();
        
        if (res.ok) {
            log(text, 'success');
        } else {
            try {
                const json = JSON.parse(text);
                log(`HTTP ${res.status}: ${JSON.stringify(json)}`, 'error');
            } catch (e) {
                const firstLine = text.split('\n')[0].replace(/<[^>]*>?/gm, '');
                log(`Server crashed! 💥 Sentry Webhook should fire immediately. [${firstLine.substring(0, 80)}...]`, 'error');
            }
        }
    } catch (e) {
        log(`Network failed: ${e.message}`, 'error');
    }
}
