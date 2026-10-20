import { Link } from "react-router-dom";

import { providerName } from "@/features/ai/lib/providers";
import { legalPath } from "../lib/legalPages";
import type { LegalContent, LegalContext } from "./types";

/* Textos legales en español (issue #3, decisión 0026). Son una base que quien
 * despliega debe revisar: no son asesoramiento legal. Lo que dependa de la
 * instalación sale del contexto; nada se inventa. */

function operator({ legal }: LegalContext) {
  return (
    <ul>
      <li>
        <strong>Titular:</strong> {legal.operator_name}
        {legal.tax_id && <> (NIF {legal.tax_id})</>}
      </li>
      {legal.address && (
        <li>
          <strong>Dirección:</strong> {legal.address}
        </li>
      )}
      <li>
        <strong>Contacto:</strong>{" "}
        <a href={`mailto:${legal.contact_email}`}>{legal.contact_email}</a>
      </li>
    </ul>
  );
}

const authority = ({ legal }: LegalContext) =>
  legal.supervisory_authority ?? "la Agencia Española de Protección de Datos (www.aepd.es)";

function aiRecipients({ legal }: LegalContext) {
  const platform = legal.ai_platform_provider;
  const ownKeys = legal.ai_own_key_providers;
  if (!platform && ownKeys.length === 0) return null;
  return (
    <>
      {platform && platform !== "ollama" && (
        <li>
          <strong>{providerName(platform)}</strong>, el proveedor de inteligencia artificial de
          esta instalación, cuando pides una propuesta con los usos gratuitos. Recibe tu perfil
          profesional <strong>sin tus datos de contacto</strong> y la descripción de la oferta.
          Está en Estados Unidos: la transferencia se ampara en el Marco de Privacidad de Datos
          UE-EE. UU. o en cláusulas contractuales tipo.
        </li>
      )}
      {platform === "ollama" && (
        <li>
          El servidor de inteligencia artificial (Ollama) que gestiona el titular, cuando pides una
          propuesta con los usos gratuitos. Recibe tu perfil profesional{" "}
          <strong>sin tus datos de contacto</strong> y la descripción de la oferta.
        </li>
      )}
      {ownKeys.length > 0 && (
        <li>
          Si usas <strong>tu propia clave</strong> de{" "}
          {new Intl.ListFormat("es", { type: "disjunction" }).format(ownKeys.map(providerName))},
          los mismos datos van a tu cuenta de ese proveedor, bajo tu propio contrato con él. Tu
          clave se guarda cifrada y nunca se muestra.
        </li>
      )}
    </>
  );
}

const content: LegalContent = {
  notice: (context) => (
    <>
      <h2>Titular</h2>
      <p>
        Esta instalación de Applications Tracker ({context.site}) la ofrece y la gestiona:
      </p>
      {operator(context)}
      <p>
        Applications Tracker es un programa que su autor publica para que cualquiera lo instale.
        El autor no gestiona esta instalación ni tiene acceso a sus datos: el responsable es el
        titular.
      </p>

      <h2>Objeto</h2>
      <p>
        La aplicación sirve para registrar y seguir tus candidaturas a puestos de trabajo: las
        solicitudes, sus estados, las entrevistas, los recordatorios, tus CVs y tus cartas. Su
        uso se rige por los <Link to={legalPath("terms")}>términos y condiciones</Link> y la{" "}
        <Link to={legalPath("privacy")}>política de privacidad</Link>.
      </p>

      <h2>Enlaces a otros sitios</h2>
      <p>
        La aplicación guarda los enlaces a las ofertas que tú añades. El titular no responde del
        contenido de esos sitios.
      </p>

      <h2>Ley aplicable</h2>
      <p>Este aviso se rige por la ley española.</p>
    </>
  ),

  privacy: (context) => {
    const { legal, emailEnabled } = context;
    return (
      <>
        <h2>Quién trata tus datos</h2>
        <p>El responsable del tratamiento es el titular de esta instalación:</p>
        {operator(context)}

        <h2>Qué datos tratamos</h2>
        <ul>
          <li>
            <strong>Tu cuenta:</strong> tu email y tu contraseña, que se guarda cifrada (con un
            hash) y nadie puede leer.
          </li>
          <li>
            <strong>Lo que registras:</strong> empresas, solicitudes y su historial, entrevistas,
            recordatorios y notas.
          </li>
          <li>
            <strong>Tu perfil profesional y tus documentos:</strong> los datos de contacto que
            pongas, tu experiencia, formación, habilidades e idiomas, y los PDF que subes o
            generas.
          </li>
          <li>
            <strong>Tus preferencias:</strong> idioma, zona horaria y avisos.
          </li>
          {(legal.ai_platform_provider || legal.ai_own_key_providers.length > 0) && (
            <li>
              <strong>Tu uso de la inteligencia artificial:</strong> las propuestas que pides, lo
              que generan y tus consentimientos.
            </li>
          )}
          <li>
            <strong>Datos técnicos:</strong> tu IP, la dirección pedida y tu navegador en los
            registros del servidor, y tu IP y email en los intentos de inicio de sesión, para
            frenar abusos.
          </li>
        </ul>

        <h2>Para qué y con qué base</h2>
        <ul>
          <li>
            <strong>Prestarte el servicio</strong> (tu cuenta y todo lo que guardas): es
            necesario para el contrato que aceptas al usarla.
          </li>
          {emailEnabled && (
            <li>
              <strong>Enviarte avisos por email</strong> (recordatorios, entrevistas, resúmenes):
              forman parte del servicio y cada uno se apaga en Preferencias.
            </li>
          )}
          {(legal.ai_platform_provider || legal.ai_own_key_providers.length > 0) && (
            <li>
              <strong>Adaptar tu CV o escribir cartas con inteligencia artificial:</strong> solo
              con tu consentimiento, que se pide para cada proveedor antes de enviarle nada y
              puedes retirar cuando quieras.
            </li>
          )}
          <li>
            <strong>Proteger la aplicación</strong> (límites de peticiones y registros): interés
            legítimo en mantenerla segura.
          </li>
          <li>
            <strong>Copias de seguridad,</strong> para recuperar tus datos si algo falla: interés
            legítimo y deber de seguridad.
          </li>
        </ul>

        <h2>A quién llegan</h2>
        <p>
          Tus datos no se venden ni se ceden. Solo los reciben, para lo que se indica, los
          proveedores que ayudan al titular a prestar el servicio:
        </p>
        <ul>
          <li>El alojamiento del servidor, si no es propio del titular.</li>
          {emailEnabled && (
            <li>El servicio de correo, que recibe tu email y el contenido de tus avisos.</li>
          )}
          {aiRecipients(context)}
        </ul>

        <h2>Cuánto tiempo</h2>
        <ul>
          <li>
            Lo que guardas, hasta que lo borras o borras tu cuenta. Al borrarla desaparece al
            momento de la aplicación y sigue como mucho{" "}
            <strong>{legal.backup_retention_days} días</strong> en las copias de seguridad, hasta
            que caducan.
          </li>
          {emailEnabled && <li>El registro de los avisos enviados, 90 días.</li>}
          <li>Los datos técnicos, el tiempo imprescindible para la seguridad.</li>
        </ul>

        <h2>Tus derechos</h2>
        <p>
          Puedes acceder a tus datos, rectificarlos, suprimirlos, oponerte a su tratamiento,
          pedir que se limite, llevártelos (portabilidad) y retirar tu consentimiento:
        </p>
        <ul>
          <li>
            <strong>Descargarlos todos</strong> en Preferencias, con «Descargar todos mis datos».
          </li>
          <li>
            <strong>Corregirlos</strong> en la propia aplicación. Para cambiar tu email, escribe
            al titular.
          </li>
          <li>
            <strong>Borrarlos</strong> con «Eliminar cuenta», en Preferencias.
          </li>
          <li>
            Para cualquier otra petición, escribe a{" "}
            <a href={`mailto:${legal.contact_email}`}>{legal.contact_email}</a>. Te responderemos
            en un mes como mucho.
          </li>
        </ul>
        <p>Si crees que no se respetan tus derechos, puedes reclamar ante {authority(context)}.</p>

        <h2>Menores</h2>
        <p>La aplicación no es para menores de 14 años.</p>

        <h2>Seguridad</h2>
        <p>
          La conexión va cifrada (HTTPS), las contraseñas se guardan con un hash, las claves de
          inteligencia artificial cifradas y se hacen copias de seguridad cada día.
        </p>

        <h2>Cambios</h2>
        <p>
          Si esta política cambia en algo importante, te pediremos que la aceptes de nuevo al
          entrar.
        </p>
      </>
    );
  },

  terms: (context) => (
    <>
      <h2>El servicio</h2>
      <p>
        El titular de esta instalación ({context.legal.operator_name}) te ofrece Applications
        Tracker para organizar tu búsqueda de empleo. Se ofrece <strong>tal cual</strong>: se
        procura que funcione y que tus datos estén a salvo, pero no se garantiza que esté
        siempre disponible ni libre de errores. Descarga tus datos de vez en cuando si son
        importantes para ti.
      </p>

      <h2>Tu cuenta</h2>
      <ul>
        <li>Es personal: no la compartas. Tienes que tener al menos 14 años.</li>
        <li>Cuida tu contraseña. Lo que se haga con tu cuenta es responsabilidad tuya.</li>
      </ul>

      <h2>Uso aceptable</h2>
      <p>No puedes usar la aplicación para:</p>
      <ul>
        <li>Guardar o compartir contenido ilegal, o datos de otras personas sin derecho a ello.</li>
        <li>Subir ficheros dañinos o intentar acceder a lo que no es tuyo.</li>
        <li>Sobrecargarla o saltarte sus límites.</li>
      </ul>

      <h2>Tu contenido</h2>
      <p>
        Lo que guardas es tuyo. Solo se usa para prestarte el servicio: guardarlo, mostrártelo,
        generar tus PDF y, si lo pides, enviarlo a la inteligencia artificial.
      </p>

      <h2>La inteligencia artificial</h2>
      <p>
        Las propuestas de CV y de cartas las genera una inteligencia artificial y pueden
        contener errores. Revísalas antes de usarlas: tú decides qué envías a cada empresa y
        respondes de que sea cierto.
      </p>

      <h2>Baja y suspensión</h2>
      <p>
        Puedes borrar tu cuenta cuando quieras, desde Preferencias. El titular puede suspender o
        borrar una cuenta que incumpla estos términos, avisándote si es posible.
      </p>

      <h2>Responsabilidad</h2>
      <p>
        El titular no responde de los daños derivados de un uso indebido de la aplicación ni de
        su indisponibilidad, salvo en lo que la ley no permita limitar.
      </p>

      <h2>Cambios</h2>
      <p>
        Si estos términos cambian en algo importante, te pediremos que los aceptes de nuevo al
        entrar.
      </p>

      <h2>Ley aplicable</h2>
      <p>
        Se rigen por la ley española. Si eres consumidor, puedes acudir a los tribunales de tu
        domicilio.
      </p>
    </>
  ),

  cookies: () => (
    <>
      <h2>Qué guardamos en tu navegador</h2>
      <ul>
        <li>
          <strong>Cookies de sesión:</strong> mantienen tu sesión iniciada. Son estrictamente
          necesarias: sin ellas no podrías entrar.
        </li>
        <li>
          <strong>Preferencias de la interfaz</strong> (en el almacenamiento del navegador, no
          son cookies): el tema claro u oscuro, el idioma de las pantallas de acceso, las columnas
          plegadas del tablero y las propuestas de IA en curso.
        </li>
      </ul>

      <h2>Lo que no hay</h2>
      <p>
        Ni analítica, ni publicidad, ni cookies de terceros. Por eso no te pedimos que aceptes
        cookies: las que hay son las imprescindibles para que la aplicación funcione.
      </p>

      <h2>Cómo borrarlas</h2>
      <p>
        Desde la configuración de tu navegador. Si borras las cookies de sesión, tendrás que
        volver a iniciar sesión.
      </p>
    </>
  ),
};

export default content;
