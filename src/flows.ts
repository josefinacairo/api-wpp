import 'dotenv/config';

export interface ServiceFlow {
    keyword: string;
    response: (numeroCuenta: string) => string;
}

export const serviceFlows: Record<string, ServiceFlow[]> = {
    EDENOR: [
        { keyword: 'Factura', response: () => 'Por favor, indícanos tu número de cliente para ayudarte con la factura.' },
        { keyword: 'Corte de luz', response: () => 'Estamos trabajando para resolver el problema en tu zona.' },
    ],
    EDESUR: [
        { keyword: '2: 💰 Consulta de saldo', response: () => '2' },
        {
            keyword: 'Introducí el número de cliente sin espacios ni letras.',
            response: (numeroCuenta: string) => `${numeroCuenta}`,  // Usamos el número de cuenta proporcionado en el POST
        },
        {
            keyword: 'Solamente ingresar números (0 al 9).',
            response: (numeroCuenta: string) => `${numeroCuenta}`,  // Usamos el número de cuenta proporcionado en el POST
        },
        {
            keyword: 'El número de cliente debe tener hasta 8 dígitos.',
            response: (numeroCuenta: string) => `${numeroCuenta}`,  // Usamos el número de cuenta proporcionado en el POST
        },
        { keyword: 'dirección registrada', response: () => '1' },
        { keyword: '¿Te puedo ayudar con algo más?', response: () => '2' },
    ],
    AYSA: [
        { keyword: '1. Estado de cuenta', response: () => '1' },
        {
            keyword: 'Para pasarte tu Estado de Cuenta 📊, necesito el número de Cuenta de Servicios que está en tu factura. ¿Lo tenés?',
            response: () => '1',
        },
        {
            keyword: 'Voy a necesitar tu número de Cuenta de Servicios, que está en tu factura, para informarte sobre tu Estado de Cuenta 📊.',
            response: () => '1',
        },
        { keyword: 'Se presentó un error, por favor intentá nuevamente.', response: () => 'SALDO' },
        {
            keyword: 'ingresá el número de cuenta de servicios:',
            response: (numeroCuenta: string) => `${numeroCuenta}`,
        },
        { keyword: '¿Querés realizar otras consultas?', response: () => '2' },
    ],
    METROGAS: [
        { keyword: 'Consulta de deuda', response: () => 'Por favor, indícanos tu número de cliente para continuar.' },
        { keyword: 'Fuga de gas', response: () => 'Llama al 0800-333-4430 para emergencias.' },
    ],
};
