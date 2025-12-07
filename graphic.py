import matplotlib.pyplot as plt
import numpy as np

# Данные из таблицы
threads = np.array([2, 4, 8, 12, 16, 32, 64, 256, 1024])
time_ms = np.array([4.99, 3.22, 1.89, 2.15, 2.45, 2.38, 3.76, 11.73, 48.72])
speedup = np.array([2.06, 3.33, 5.5, 4.92, 4.22, 4.80, 2.84, 0.93, 0.23])
efficiency = np.array([1.03214, 0.83365, 0.68725, 0.41023, 0.26377, 0.15011, 0.04437, 0.00361, 0.00023])

# Основной график ускорения
plt.figure(figsize=(10, 6))
plt.plot(threads, speedup, 'bo-', linewidth=2, markersize=8, label='Измеренное ускорение')


# Отмечаем точку максимального ускорения
max_speedup_idx = np.argmax(speedup)
plt.plot(threads[max_speedup_idx], speedup[max_speedup_idx], 'ro', markersize=10, 
         label=f'Максимум: {speedup[max_speedup_idx]:.1f} при {threads[max_speedup_idx]} потоках')

plt.xscale('log')
plt.xlabel('Количество потоков')
plt.ylabel('Ускорение')
plt.title('Зависимость ускорения от количества потоков')
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig('speedup_plot.png', dpi=300, bbox_inches='tight')
print("График сохранен как 'speedup_plot.png'")

# График времени выполнения
plt.figure(figsize=(10, 6))
plt.plot(threads, time_ms, 'go-', linewidth=2, markersize=6)
plt.xscale('log')
plt.yscale('log')
plt.xlabel('Количество потоков')
plt.ylabel('Время выполнения (мс)')
plt.title('Зависимость времени выполнения от количества потоков')
plt.grid(True, alpha=0.3)
plt.savefig('time_plot.png', dpi=300, bbox_inches='tight')
print("График сохранен как 'time_plot.png'")

# График эффективности
plt.figure(figsize=(10, 6))
plt.plot(threads, efficiency, 'mo-', linewidth=2, markersize=6)
plt.xscale('log')
plt.xlabel('Количество потоков')
plt.ylabel('Эффективность')
plt.title('Зависимость эффективности от количества потоков')
plt.grid(True, alpha=0.3)
plt.savefig('efficiency_plot.png', dpi=300, bbox_inches='tight')
print("График сохранен как 'efficiency_plot.png'")

# Анализ результатов
print("\nАНАЛИЗ РЕЗУЛЬТАТОВ:")
print(f"Максимальное ускорение: {speedup[max_speedup_idx]:.2f} при {threads[max_speedup_idx]} потоках")
print(f"Оптимальный диапазон потоков: 4-16 (ускорение > 3.0)")
print(f"Критическая точка: после 64 потоков резкое падение производительности")
print(f"Эффективность > 80% сохраняется до {threads[np.where(efficiency > 0.8)[0][-1]]} потоков")
