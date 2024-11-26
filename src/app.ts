import { createBot, createFlow, createProvider, addKeyword, MemoryDB } from '@bot-whatsapp/bot';
import { BaileysProvider, handleCtx } from '@bot-whatsapp/provider-baileys';
import { serviceFlows } from './flows';
import 'dotenv/config';
import { createClient, RedisClientType } from 'redis';

// Configura Redis
const client: RedisClientType = createClient();
await client.connect();

client.on('connect', () => {
    console.log('Conectado a Redis');
});

// Función para obtener saldo de Redis
const getSaldoFromRedis = async (numeroCuenta: string, servicio: string): Promise<string | null> => {
    const dbKey = `${numeroCuenta}-${servicio}`;
    try {
        const saldo = await client.hGet(dbKey, 'saldo');
        if (!saldo) {
            console.warn(`Clave no encontrada en Redis: ${dbKey}`);
            return null;
        }
        console.log(`Saldo recuperado de Redis: ${saldo}`);
        return saldo;
    } catch (error) {
        console.error(`Error al recuperar saldo desde Redis para clave ${dbKey}:`, error);
        return null;
    }
};

// Función para manejar preguntas y respuestas dinámicamente con el número de cuenta
const handleServiceMessage = async (
    provider: any,
    from: string,
    body: string,
    numeroCuenta: string, 
    db: any 
): Promise<boolean> => {
    const noSaldoPhrases = process.env.NO_SALDO_PHRASES?.split(',').map(phrase => phrase.trim()).join('|') || "no saldo pendiente";
    const noSaldoRegex = new RegExp(noSaldoPhrases, 'i');
    const saldoRegex = /\$\s?((?:\d{1,3}(?:[.,]\d{3})*[.,]\d{2})|\d+)/;

    for (const [service, flow] of Object.entries(serviceFlows)) {
        const serviceNumber = process.env[`${service}_NUM`];
        if (from === serviceNumber) {
            for (const { keyword, response } of flow) {
                if (body.includes(keyword)) {
                    const responseWithAccount = response(numeroCuenta); 
                    await provider.sendMessage(from, responseWithAccount, {});

                    let saldo = "0";
                    if (noSaldoRegex.test(body)) {
                        saldo = "0";
                        console.log("No hay saldo pendiente, estableciendo saldo a 0.");
                    } else {
                        const match = body.match(saldoRegex);
                        if (match) {
                            saldo = match[1];
                            console.log(`Saldo detectado en la respuesta: ${saldo}`);
                        }
                    }

                    const dbKey = `${numeroCuenta}-${service}`;
                    const context = { key: dbKey, value: { saldo }, timestamp: new Date().toISOString() };

                    await client.hSet(dbKey, { saldo, timestamp: context.timestamp });
                    console.log(`Datos guardados en Redis con key ${dbKey}`);

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

    provider.http?.server.post('/update-balance', handleCtx(async (bot, req, res) => {
        try {
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
                    res.status(404).end(`No se encontró el número para el servicio ${servicio}.`);
                }
            } else {
                res.status(400).end(`Servicio no permitido. Usa uno de los siguientes: ${serviciosPermitidos.join(', ')}.`);
            }
        } catch (error) {
            console.error(`Error en el endpoint /update-balance:`, error);
            res.status(500).json({ error: 'Error al procesar la solicitud.' });
        }
    }));

    provider.http?.server.get('/get-balance', async (req, res) => {
        try {
            const { servicio, numeroCuenta } = req.query;

            if (!servicio || !numeroCuenta) {
                return res.status(400).json({ error: 'Faltan parámetros: servicio y numeroCuenta son requeridos.' });
            }

            const saldo = await getSaldoFromRedis(numeroCuenta as string, servicio as string);

            if (saldo) {
                res.json({ servicio, numeroCuenta, saldo });
            } else {
                res.status(404).json({ error: 'Saldo no encontrado para esta cuenta y servicio.' });
            }
        } catch (error) {
            console.error('Error al procesar la solicitud:', error);
            res.status(500).json({ error: 'Error interno del servidor.' });
        }
    });

    // No se usa más MemoryDB, solo Redis para almacenamiento persistente
    console.log('Configuración de Redis');

    provider.on('message', async (message: any) => {
        const from: string = message.from;
        const body: string = message.body;

        console.log(`Mensaje recibido de ${from}: ${body}`);

        try {
            const processed = await handleServiceMessage(provider, from, body, nroCta, null); // Pasamos null porque no necesitamos MemoryDB aquí

            if (!processed) {
                console.log(`No se encontró un flujo para el mensaje: ${body}`);
            }
        } catch (error) {
            console.error(`Error al procesar el mensaje:`, error);
            await provider.sendMessage(from, "Ha ocurrido un error. Por favor, intenta más tarde.", {});
        }
    });

    await createBot({
        flow: createFlow([flowBienvenida]),
        database: new MemoryDB(), // No usamos MemoryDB, no se pasa nada aquí
        provider,
    });
};

main().catch((err) => {
    console.error('Error al iniciar el bot:', err);
    process.exit(1); // Asegura que el proceso termine en caso de error
});

client.on('error', (err) => {
    console.error('Error en Redis:', err);
    setTimeout(() => client.connect(), 5000);
});
