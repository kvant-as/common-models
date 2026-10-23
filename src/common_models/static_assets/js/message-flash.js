// Общий модуль всплывающих уведомлений (flash-сообщений) для enPlans и
// erespondentN — раньше был продублирован в обоих приложениях и успел
// разъехаться (в erespondentN осталась старая реализация без стопки a-ля
// iOS). Теперь один источник, расшаренный через common-models.
//
// Уведомления накладываются друг на друга стопкой (как группа уведомлений
// на iOS), а не растут отдельным списком вниз/вверх — самое новое сверху и
// полностью видимо, более старые чуть выглядывают из-под него (меньше,
// прозрачнее). Наведение на стопку разворачивает её в обычный список (см.
// .stack-expanded в message-flash.css и updateMessagesDisplay ниже).
//
// Иконки у каждого приложения лежат по-разному (enPlans: /static/img/,
// erespondentN: /static/img/svg/) — путь передаётся в init(options).
const messageFlash = (function () {
    const containerId = 'flash-container';
    let container;
    let messages = [];
    const DISPLAY_TIME = 30000;
    let autoRemoveTimers = {};
    let iconBasePath = '/static/img';

    function init(options = {}) {
        if (options.iconBasePath) iconBasePath = options.iconBasePath;

        container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            document.body.appendChild(container);
        }

        const storedMessages = JSON.parse(localStorage.getItem('flashMessages') || '[]');
        const now = Date.now();
        messages = storedMessages.filter(msg => now - msg.createdAt < DISPLAY_TIME);

        localStorage.setItem('flashMessages', JSON.stringify(messages));
        renderMessages();

        // Наведение на стопку уведомлений разворачивает её в обычный
        // список (как долгое нажатие на группу уведомлений в iOS) —
        // иначе старые сообщения были бы видны только краешком и до
        // кнопки закрытия/текста было бы не добраться.
        container.addEventListener('mouseenter', () => {
            container.classList.add('stack-expanded');
            updateMessagesDisplay();
        });
        container.addEventListener('mouseleave', () => {
            container.classList.remove('stack-expanded');
            updateMessagesDisplay();
        });
    }

    function _showMessage(msgObj) {
        const alertBox = document.createElement('div');
        alertBox.className = `custom-alert ${msgObj.type === 'error' ? 'alert-danger' : 'alert-success'}`;
        alertBox.dataset.msgId = msgObj.id;

        const imgSrc = msgObj.type === 'error'
            ? `${iconBasePath}/Error.svg`
            : `${iconBasePath}/Checkmark.svg`;

        let messageText = msgObj.msg;
        let isLong = messageText && messageText.length > 80;
        let displayText = isLong ? messageText.substring(0, 80) + '...' : messageText;

        alertBox.innerHTML = `
            <img src="${imgSrc}" class="alert-icon" alt="">
            <div class="p_message_cont">
                <p>${displayText}</p>
                ${isLong ? '<span class="expand-hint">нажмите для развертывания</span>' : ''}
            </div>
            <button class="alert-close">&times;</button>
        `;

        if (isLong) {
            const fullText = messageText;
            const pElement = alertBox.querySelector('.p_message_cont p');
            const hintElement = alertBox.querySelector('.expand-hint');

            alertBox.addEventListener('click', (e) => {
                if (e.target.classList.contains('alert-close')) return;

                if (alertBox.classList.contains('collapsed')) {
                    pElement.textContent = fullText;
                    hintElement.textContent = 'нажмите для сворачивания';
                    alertBox.classList.remove('collapsed');
                    alertBox.classList.add('expanded');
                } else {
                    pElement.textContent = displayText;
                    hintElement.textContent = 'нажмите для развертывания';
                    alertBox.classList.remove('expanded');
                    alertBox.classList.add('collapsed');
                }
            });
        }

        alertBox.querySelector('.alert-close').addEventListener('click', e => {
            e.stopPropagation();
            removeMessage(alertBox, msgObj);
        });

        container.insertBefore(alertBox, container.firstChild);

        const timerId = setTimeout(() => {
            if (container.contains(alertBox)) {
                removeMessage(alertBox, msgObj);
            }
        }, DISPLAY_TIME);

        autoRemoveTimers[msgObj.id] = timerId;

        updateMessagesDisplay();
    }

    function removeMessage(alertBox, msgObj) {
        if (autoRemoveTimers[msgObj.id]) {
            clearTimeout(autoRemoveTimers[msgObj.id]);
            delete autoRemoveTimers[msgObj.id];
        }

        // Сбрасываем inline transform/opacity, которые проставляет
        // updateMessagesDisplay для раскладки стопки — иначе они (как
        // более специфичные) перебивают анимацию выезда из .removing.
        alertBox.style.transform = '';
        alertBox.style.opacity = '';
        alertBox.classList.add('removing');
        setTimeout(() => {
            if (container.contains(alertBox)) container.removeChild(alertBox);
            messages = messages.filter(m => m.id !== msgObj.id);
            localStorage.setItem('flashMessages', JSON.stringify(messages));
            updateMessagesDisplay();
        }, 300);
    }

    function addMessage(msg, type = 'success') {
        const msgObj = {
            id: Date.now() + '_' + Math.random().toString(36).substr(2, 9),
            msg,
            type,
            createdAt: Date.now()
        };
        messages.unshift(msgObj);
        localStorage.setItem('flashMessages', JSON.stringify(messages));
        _showMessage(msgObj);
    }

    function renderMessages() {
        container.innerHTML = '';
        Object.keys(autoRemoveTimers).forEach(key => {
            clearTimeout(autoRemoveTimers[key]);
            delete autoRemoveTimers[key];
        });

        messages.sort((a, b) => b.createdAt - a.createdAt);
        messages.forEach(msg => _showMessage(msg));
    }

    // Сколько карточек позади самой новой ещё выглядывают из-под неё —
    // остальные (если сообщений больше) просто скрыты (opacity 0), но
    // остаются в DOM и по-прежнему посчитаны таймером авто-закрытия.
    const MAX_PEEK = 3;

    function updateMessagesDisplay() {
        const alerts = Array.from(container.querySelectorAll('.custom-alert'));
        const isStackExpanded = container.classList.contains('stack-expanded');

        alerts.forEach((alert, index) => {
            const pElement = alert.querySelector('.p_message_cont p');
            const hintElement = alert.querySelector('.expand-hint');
            const msgObj = messages.find(m => m.id === alert.dataset.msgId);

            if (index === 0) {
                alert.classList.remove('collapsed');
                alert.classList.add('expanded');
                if (msgObj && msgObj.msg.length > 80) {
                    pElement.textContent = msgObj.msg;
                    if (hintElement) {
                        hintElement.textContent = 'нажмите для сворачивания';
                    }
                }
            } else {
                alert.classList.add('collapsed');
                alert.classList.remove('expanded');
                if (msgObj && msgObj.msg.length > 80) {
                    pElement.textContent = msgObj.msg.substring(0, 80) + '...';
                    if (hintElement) {
                        hintElement.textContent = 'нажмите для развертывания';
                    }
                }
            }

            if (isStackExpanded) {
                // Развёрнуто — обычный flex-список, раскладку делает CSS,
                // никаких inline-стилей позиции тут не нужно.
                alert.style.transform = '';
                alert.style.opacity = '';
                alert.style.zIndex = '';
                alert.style.pointerEvents = '';
            } else if (index >= MAX_PEEK) {
                alert.style.transform = 'translateY(0) scale(0.86)';
                alert.style.opacity = '0';
                alert.style.zIndex = String(alerts.length - index);
                alert.style.pointerEvents = 'none';
            } else {
                alert.style.transform = `translateY(-${index * 10}px) scale(${1 - index * 0.05})`;
                alert.style.opacity = String(1 - index * 0.3);
                alert.style.zIndex = String(alerts.length - index);
                // Пока стопка свёрнута, кликабельна только передняя (самая
                // новая) карточка — как в iOS, чтобы случайно не попасть
                // по кнопке закрытия карточки, которая визуально скрыта
                // позади.
                alert.style.pointerEvents = index === 0 ? 'auto' : 'none';
            }
        });

        if (!isStackExpanded) {
            const topAlert = alerts[0];
            container.style.height = topAlert ? `${topAlert.offsetHeight}px` : '0px';
        } else {
            container.style.height = '';
        }
    }

    return { init, addMessage };
})();
