import type { APIRoute } from 'astro';
import nodemailer from 'nodemailer';

function escapeHtml(value: string) {
    // Escape submitted text before placing it in HTML email content to prevent
    // message markup from altering or injecting content into the recipient email.
    return value
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

export const POST: APIRoute = async ({ request }) => {
    let data: unknown;

    try {
        data = await request.json();
    } catch {
        return new Response('Invalid form data.', { status: 400 });
    }

    if (!data || typeof data !== 'object') {
        return new Response('Invalid form data.', { status: 400 });
    }

    const { name, email, message } = data as Record<string, unknown>;

    if (
        typeof name !== 'string' || !name.trim() ||
        typeof email !== 'string' || !email.trim() ||
        typeof message !== 'string' || !message.trim()
    ) {
        return new Response('Please complete every field.', { status: 400 });
    }

    const {
        GMAIL_USER,
        GMAIL_APP_PASSWORD,
        CONTACT_RECIPIENT
    } = import.meta.env;

    if (!GMAIL_USER || !GMAIL_APP_PASSWORD || !CONTACT_RECIPIENT) {
        return new Response('Contact email is not configured.', { status: 500 });
    }

    const transporter = nodemailer.createTransport({
        service: 'gmail',
        connectionTimeout: 15_000,
        greetingTimeout: 15_000,
        socketTimeout: 15_000,
        auth: {
            user: GMAIL_USER,
            pass: GMAIL_APP_PASSWORD
        }
    });

    try {
        await transporter.sendMail({
            from: GMAIL_USER,
            to: CONTACT_RECIPIENT,
            replyTo: email.trim(),
            subject: `Research Survey contact from ${name.trim()}`,
            text: `Name: ${name.trim()}\nEmail: ${email.trim()}\n\n${message.trim()}`,
            html: `
                <p><strong>Name:</strong> ${escapeHtml(name.trim())}</p>
                <p><strong>Email:</strong> ${escapeHtml(email.trim())}</p>
                <p><strong>Message:</strong></p>
                <p>${escapeHtml(message.trim()).replace(/\n/g, '<br>')}</p>
            `
        });
    } catch (error) {
        // Provider details help distinguish authentication, SMTP, and recipient
        // configuration problems without exposing them in the user response.
        console.error('Unable to send contact email:', error);
        return new Response('Unable to send your message. Please try again.', { status: 502 });
    }

    return new Response(null, { status: 200 });
};
