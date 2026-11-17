---
status: accepted
---

# La Pantalla de llamados se accede sin sesión, con un televisor vinculado por código

La Pantalla de llamados corre en el navegador de un televisor que queda encendido todo el día sin nadie que lo opere, y el sistema está publicado en internet. Decidimos que el televisor no inicie sesión como el resto del sistema: abre una dirección corta, muestra un código de seis caracteres y el director lo carga en el sistema para vincularlo. Desde ese momento el televisor se identifica con una clave secreta larga que guarda el propio navegador y que el director puede revocar. Es la única consulta que entrega datos de pacientes sin sesión de Flask-Login, y es deliberado.

## Considered Options

- **Usuario del sistema para el televisor.** Descartado: la sesión vence y alguien tendría que reingresar la contraseña con el control remoto. Con un rol existente el televisor quedaría con acceso a pacientes e historias, y un rol nuevo rompe la regla de mantener exactos los cuatro roles (`director`, `profesional`, `administrativo`, `area`).
- **Dirección pública sin clave.** Descartado: cualquiera que conozca la dirección vería desde afuera quién está en la sala de espera.
- **Enlace con la clave secreta dentro de la dirección.** Descartado: escribir unos 32 caracteres con el control remoto es impracticable, y la clave quedaría en el historial del navegador y en los registros de Nginx.

## Consequences

- La consulta de la pantalla es de solo lectura y devuelve únicamente lo que se muestra: Nombre abreviado, Consultorio y nombre del profesional. El nombre se abrevia en el servidor; el nombre completo, el DNI, la especialidad y el motivo nunca viajan al televisor.
- El pedido de código es el único punto del sistema que cualquiera puede invocar sin sesión y que escribe en la base. Un código sin vincular no da acceso a nada, vence a los pocos minutos y la cantidad de pedidos pendientes está acotada.
- La clave vive en el almacenamiento del navegador del televisor. Si el televisor lo borra, hay que vincularlo de nuevo.
- Quien obtenga la clave ve lo mismo que se ve en la sala de espera, hasta que el director la revoque. No hay que ampliar esa consulta con más datos del paciente sin revisar esta decisión.
