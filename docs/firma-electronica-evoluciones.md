# Firma electrónica de evoluciones

La evolución clínica se cierra mediante una firma electrónica vinculada a:

- la sesión autenticada de Flask-Login;
- el usuario, rol y matrícula profesional;
- la validación explícita de la matrícula por CAU;
- una confirmación visible de “Firmar evolución”;
- el contenido clínico exacto, versionado y protegido con SHA-256;
- la fecha y hora de la actuación;
- una auditoría append-only.

No se solicita nuevamente la contraseña y no se genera un certificado de firma
digital. La implementación es una firma electrónica; la institución conserva
la responsabilidad de administrar las cuentas, sus sesiones y la validación de
las matrículas.

## Validación de matrículas

La migración deja `usuarios.matricula_verificada = 0`. Luego de la comprobación
institucional, CAU debe marcar la matrícula directamente en la base de datos,
registrando quién y cuándo la validó:

```sql
UPDATE usuarios
SET matricula_verificada = 1,
    matricula_verificada_en = NOW(6),
    matricula_verificada_por = <usuario_cau_id>
WHERE id = <profesional_id>
  AND rol IN ('profesional', 'director')
  AND matricula_tipo IS NOT NULL
  AND matricula_numero IS NOT NULL;
```

Si se modifica el tipo, número o provincia de matrícula desde la administración
del sistema, la validación se revoca automáticamente y debe repetirse.

## Evoluciones existentes

Las evoluciones anteriores a esta migración no se firman retroactivamente. Se
mantienen como registros históricos; las nuevas evoluciones y rectificaciones
deben quedar firmadas. Una rectificación requiere un motivo, crea una nueva
versión y conserva la anterior sin sobrescribirla.

## Documentos generales de la historia

Los estudios externos, antecedentes y consentimientos que no son evoluciones
se cargan desde la sección **Documentos de la historia**. Pueden incorporarlos
los cuatro roles autenticados del sistema. Cada archivo se guarda en un
directorio aislado por paciente y queda registrado en `historia_archivos` con
nombre original, tipo, tamaño, usuario, fecha de carga y huella SHA-256.

Los archivos permitidos son PDF, JPG y PNG de hasta 10 MB. La API verifica
extensión, tipo MIME y firma binaria básica; no existe operación de reemplazo o
borrado. La descarga siempre pasa por una ruta autenticada y acotada al
paciente. El PDF completo lista estos documentos con su fecha, cargador y
huella; el original se conserva en el almacenamiento del sistema.
