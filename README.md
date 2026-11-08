# Gestor de colas de sucursal

Aplicación de terminal para gestionar tickets de `deposito`, `retiro` y
`gestion_cuenta`. Requiere Python 3 y no necesita dependencias adicionales.

## Ejecución

```bash
python3 branch_queue.py
```

El menú permite emitir tickets, llamar o consultar al siguiente cliente de un
servicio, listar las colas y ver las estadísticas. Cada servicio conserva su
propio orden de llegada y los números de ticket son globales.

Las colas y el siguiente número se guardan automáticamente en
`branch_queue_data.json`, junto al programa, tras cada emisión o llamada. El
archivo se recupera al reiniciar y no se incluye en Git. Si no se puede leer o
guardar el estado, la aplicación informa del error.

Los archivos de estado creados con los nombres de campos anteriores siguen
siendo compatibles y se actualizan al guardar el siguiente cambio.

La estructura de las colas y las consideraciones de concurrencia se explican en
[DESIGN.md](DESIGN.md).