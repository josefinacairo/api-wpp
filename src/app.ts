import { createBot, createFlow, MemoryDB, createProvider, addKeyword } from '@bot-whatsapp/bot';
import { BaileysProvider, handleCtx } from '@bot-whatsapp/provider-baileys';
import { serviceFlows } from './flows'; // Asumo que aquí tienes el archivo de los flujos
import 'dotenv/config';

// Función para manejar preguntas y respuestas dinámicamente con el número de cuenta
const handleServiceMessage = async (
    provider: any,
    from: string,
    body: string,
    numeroCuenta: string // Número de cuenta recibido desde el cuerpo del mensaje
): Promise<boolean> => {
    for (const [service, flow] of Object.entries(serviceFlows)) {
        const serviceNumber = process.env[`${service}_NUM`];

        if (from === serviceNumber) {
            for (const { keyword, response } of flow) {
//                console.log(`EL nro de cuenta es: ${numeroCuenta}`);
                if (body.includes(keyword)) {
                    const responseWithAccount = response(numeroCuenta); 
                    await provider.sendMessage(from, responseWithAccount, {});
                    return true;
                }
            }
        }
    }
    return false;
};

// Flujo de bienvenida
const flowBienvenida = addKeyword('KE').addAnswer('¡Hola! Bienvenido.');

const main = async (): Promise<void> => {
    const provider = createProvider(BaileysProvider);

    provider.initHttpServer(3002);

    let nroCta: string = " ";


    provider.http?.server.post(
        '/send-message',
        handleCtx(async (bot, req, res) => {
            const { servicio, numeroCuenta } = req.body;

            const serviciosPermitidos = Object.keys(serviceFlows);

            if (serviciosPermitidos.includes(servicio)) {
                const numeroEnvVar = `${servicio}_NUM`;
                const numero = process.env[numeroEnvVar];

                if (numero) {
                    await bot.sendMessage(numero, 'SALDO', {});
                    res.end(`Mensaje enviado a ${servicio} con número de cuenta: ${numeroCuenta}.`);
                    nroCta = numeroCuenta;
                } else {
                    res.end(`No se encontró el número para el servicio ${servicio}.`);
                }
            } else {
                res.end(
                    `Servicio no permitido. Usa uno de los siguientes: ${serviciosPermitidos.join(', ')}.`
                );
            }
        })
    );

    provider.on('message', async (message: any) => {
        const from: string = message.from; // Número de origen
        const body: string = message.body; // Contenido del mensaje recibido

        console.log(`Mensaje recibido de ${from}: ${body}`);

        // Regex para extraer el saldo
        const saldoRegex = /\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)/;
        const match = body.match(saldoRegex);

        if (match) {
            const saldo = match[1]; // Capturar el saldo
            const serviceName = Object.keys(serviceFlows).find(
                (service) => process.env[`${service}_NUM`] === from
            );

            if (serviceName) {
                console.log(`Saldo para ${serviceName}: $${saldo}`);
            }
        }

        // Obtener el número de cuenta del mensaje
//        const numeroCuentaMatch = body.match(/Número de cuenta: (\S+)/);
//       const numeroCuenta = numeroCuentaMatch ? numeroCuentaMatch[1] : '';

        // Procesar el mensaje con el flujo dinámico y el número de cuenta
        const processed = await handleServiceMessage(provider, from, body, nroCta);

        if (!processed) {
            console.log(`No se encontró un flujo para el mensaje: ${body}`);
        }
    });

    await createBot({
        flow: createFlow([flowBienvenida]),
        database: new MemoryDB(), 
        provider,
    });
};

main().catch((err) => console.error(err));
