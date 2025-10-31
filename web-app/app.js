// Инициализация Telegram Web App
const tg = window.Telegram.WebApp;

// Инициализация приложения
function initApp() {
    tg.expand();
    tg.enableClosingConfirmation();
    
    // Показываем информацию о пользователе
    const user = tg.initDataUnsafe.user;
    if (user) {
        document.getElementById('userInfo').textContent = 
            `@${user.username || 'Пользователь'}`;
    }
    
    // Загружаем данные
    loadUserData();
}

// Загрузка данных пользователя
async function loadUserData() {
    try {
        const response = await fetch('/api/user-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                initData: tg.initData
            })
        });
        
        const data = await response.json();
        updateUI(data);
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// Обновление интерфейса
function updateUI(data) {
    // Обновляем список кредитов
    const creditsList = document.getElementById('creditsList');
    creditsList.innerHTML = '';
    
    if (data.credits && data.credits.length > 0) {
        data.credits.forEach(credit => {
            const creditCard = document.createElement('div');
            creditCard.className = `credit-card ${credit.current_debt === 0 ? 'paid' : ''}`;
            creditCard.innerHTML = `
                <h3>${formatMoney(credit.debt_amount)} ₽ под ${credit.annual_rate}%</h3>
                <p>Текущий долг: ${formatMoney(credit.current_debt)} ₽</p>
                <p>Платеж: ${formatMoney(credit.monthly_payment)} ₽/мес</p>
                <p>Осталось месяцев: ${credit.months - credit.months_paid}</p>
                <button onclick="makePayment(${credit.id})" class="btn-primary" ${credit.current_debt === 0 ? 'disabled' : ''}>
                    💰 Внести платеж
                </button>
            `;
            creditsList.appendChild(creditCard);
        });
    } else {
        creditsList.innerHTML = '<p>У вас пока нет кредитов</p>';
    }
    
    // Обновляем статистику
    document.getElementById('totalDebt').textContent = formatMoney(data.total_debt || 0) + ' ₽';
    document.getElementById('monthlyPayments').textContent = formatMoney(data.monthly_payments || 0) + ' ₽';
    document.getElementById('totalOverpayment').textContent = formatMoney(data.total_overpayment || 0) + ' ₽';
}

// Управление вкладками
function openTab(tabName) {
    // Скрываем все вкладки
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Убираем активный класс у всех кнопок
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Показываем выбранную вкладку
    document.getElementById(tabName).classList.add('active');
    event.currentTarget.classList.add('active');
}

// Форма добавления кредита
function showAddCreditForm() {
    document.getElementById('addCreditForm').classList.remove('hidden');
}

function hideAddCreditForm() {
    document.getElementById('addCreditForm').classList.add('hidden');
}

async function addCredit(event) {
    event.preventDefault();
    
    const formData = {
        debt_amount: parseFloat(document.getElementById('debtAmount').value),
        annual_rate: parseFloat(document.getElementById('interestRate').value),
        months: parseInt(document.getElementById('loanTerm').value)
    };
    
    try {
        const response = await fetch('/api/add-credit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                initData: tg.initData,
                ...formData
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            hideAddCreditForm();
            loadUserData(); // Перезагружаем данные
            tg.showPopup({
                title: 'Успех!',
                message: 'Кредит успешно добавлен'
            });
        }
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

// Внесение платежа
async function makePayment(creditId) {
    const amount = prompt('Введите сумму платежа:');
    if (amount && !isNaN(amount)) {
        try {
            const response = await fetch('/api/make-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    initData: tg.initData,
                    credit_id: creditId,
                    amount: parseFloat(amount)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                loadUserData();
                tg.showPopup({
                    title: 'Платеж внесен!',
                    message: `Платеж ${amount} ₽ успешно обработан`
                });
            }
        } catch (error) {
            console.error('Ошибка:', error);
        }
    }
}

// Вспомогательные функции
function formatMoney(amount) {
    return new Intl.NumberFormat('ru-RU').format(amount);
}

// Инициализация приложения при загрузке
document.addEventListener('DOMContentLoaded', initApp);
