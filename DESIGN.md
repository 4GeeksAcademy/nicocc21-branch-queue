# Diseño de las colas

Cada servicio tiene su propio `collections.deque`. Añadir un ticket al final,
consultar el primero y retirarlo del principio son operaciones O(1), sin
recorrer tickets de otros servicios. Con una única cola compartida habría que
buscar el primer ticket del servicio solicitado, lo que puede tomar O(n).
El guardado del JSON completo sí requiere O(n), por lo que la operación pública
de emisión o llamada no es O(1) en su conjunto.

## Agentes concurrentes

Si dos agentes del mismo servicio consultan el primer ticket antes de retirarlo,
ambos podrían llamar al mismo cliente. Para evitarlo, hay que comprobar y
retirar el ticket de la cola de forma atómica, antes de anunciar al cliente.
Con persistencia, la retirada también debe confirmarse en el estado compartido
antes de anunciarla; si falla, no se debe llamar al cliente. La sincronización
debe proteger toda la operación y el contador global para impedir conflictos.

La aplicación actual es un programa de terminal de un solo proceso y no
implementa sincronización entre hilos ni entre procesos. Para soportar agentes
concurrentes habría que incorporar una estrategia de bloqueo y estado
compartido adecuada; el reemplazo atómico del archivo por sí solo no basta.
