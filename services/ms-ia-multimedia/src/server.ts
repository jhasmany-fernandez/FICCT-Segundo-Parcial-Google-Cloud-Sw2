import amqp, { ConsumeMessage } from "amqplib";
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import express from "express";
import multer from "multer";
import { randomUUID } from "node:crypto";
import path from "node:path";
import OpenAI from "openai";
import { Counter, Registry, collectDefaultMetrics } from "prom-client";

type AnalyzeEmergencyRequest = {
  emergency_id: number;
  description: string;
  source: string;
};

type AnalyzeEmergencyResult = {
  status: "ok";
  service: "ms-ia-multimedia";
  emergency_id: number;
  classification: string;
  priority: string;
  summary: string;
  recommendation: string;
};

type StructuredTextAnalysis = {
  classification: string;
  priority: string;
  summary: string;
  recommendation: string;
};

type ImageAnalysis = {
  damage_detected: boolean;
  severity: string;
  summary: string;
  recommendation: string;
};

type ImageAnalyzeResponse = {
  status: "ok";
  service: "ms-ia-multimedia";
  emergency_id: number | null;
  image_analysis: ImageAnalysis;
};

type AudioAnalysis = {
  transcription: string;
  detected_issue: string;
  severity: string;
  summary: string;
  recommendation: string;
};

type AudioAnalyzeResponse = {
  status: "ok";
  service: "ms-ia-multimedia";
  emergency_id: number;
  audio_analysis: AudioAnalysis;
};

const app = express();
const port = Number(process.env.PORT ?? 8080);
const rabbitmqUrl = process.env.RABBITMQ_URL ?? "amqp://guest:guest@rabbitmq:5672/";
const analysisQueue = process.env.RABBITMQ_ANALYSIS_QUEUE ?? "emergency.analysis.requested";
const s3Endpoint = process.env.S3_ENDPOINT ?? "http://minio:9000";
const s3AccessKey = process.env.S3_ACCESS_KEY ?? "minioadmin";
const s3SecretKey = process.env.S3_SECRET_KEY ?? "minioadmin";
const s3Bucket = process.env.S3_BUCKET ?? "emergencias-evidencias";
const s3ForcePathStyle = (process.env.S3_FORCE_PATH_STYLE ?? "true").toLowerCase() === "true";
const openAiApiKey = process.env.OPENAI_API_KEY?.trim() ?? "";
const openAiModel = process.env.OPENAI_MODEL?.trim() || "gpt-4o-mini";
const openAiTranscriptionModel =
  process.env.OPENAI_TRANSCRIPTION_MODEL?.trim() || "gpt-4o-mini-transcribe";
const allowedImageTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
const allowedAudioTypes = new Set([
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/webm",
  "audio/ogg",
]);

const evidenceUpload = multer({ storage: multer.memoryStorage() });
const imageUpload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 5 * 1024 * 1024,
  },
});
const audioUpload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 15 * 1024 * 1024,
  },
});

const s3Client = new S3Client({
  endpoint: s3Endpoint,
  credentials: {
    accessKeyId: s3AccessKey,
    secretAccessKey: s3SecretKey,
  },
  forcePathStyle: s3ForcePathStyle,
  region: "us-east-1",
});

const metricsRegistry = new Registry();
collectDefaultMetrics({ register: metricsRegistry });

const httpRequestsTotal = new Counter({
  name: "ms_ia_multimedia_http_requests_total",
  help: "Total HTTP requests handled by ms-ia-multimedia",
  labelNames: ["method", "route", "status_code"] as const,
  registers: [metricsRegistry],
});

app.use(express.json());
app.use((request, response, next) => {
  response.on("finish", () => {
    const route = request.route?.path ?? request.path;
    httpRequestsTotal.inc({
      method: request.method,
      route,
      status_code: String(response.statusCode),
    });
  });

  next();
});

function buildFallbackTextResponse(payload: AnalyzeEmergencyRequest): AnalyzeEmergencyResult {
  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: payload.emergency_id,
    classification: "diagnostico_preliminar",
    priority: "media",
    summary: "Analisis simulado de emergencia vehicular",
    recommendation: "Revisar bateria, alternador y sistema de encendido.",
  };
}

function buildFallbackImageResponse(emergencyId: number | null): ImageAnalyzeResponse {
  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: emergencyId,
    image_analysis: {
      damage_detected: true,
      severity: "media",
      summary: "Analisis visual preliminar simulado de la evidencia vehicular",
      recommendation: "Revisar la zona afectada y solicitar inspeccion tecnica.",
    },
  };
}

function buildFallbackAudioResponse(emergencyId: number): AudioAnalyzeResponse {
  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: emergencyId,
    audio_analysis: {
      transcription: "Transcripcion simulada del audio de emergencia vehicular",
      detected_issue: "posible falla mecanica",
      severity: "media",
      summary: "Analisis preliminar del audio recibido",
      recommendation: "Solicitar revision tecnica y confirmar sintomas con el conductor.",
    },
  };
}

function isAnalyzeEmergencyRequest(value: unknown): value is AnalyzeEmergencyRequest {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.emergency_id === "number"
    && Number.isFinite(candidate.emergency_id)
    && typeof candidate.description === "string"
    && candidate.description.trim().length >= 3
    && typeof candidate.source === "string"
    && candidate.source.trim().length >= 2
  );
}

function isStructuredTextAnalysis(value: unknown): value is StructuredTextAnalysis {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.classification === "string"
    && typeof candidate.priority === "string"
    && typeof candidate.summary === "string"
    && typeof candidate.recommendation === "string"
  );
}

function isImageAnalysis(value: unknown): value is ImageAnalysis {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.damage_detected === "boolean"
    && typeof candidate.severity === "string"
    && typeof candidate.summary === "string"
    && typeof candidate.recommendation === "string"
  );
}

function isAudioAnalysis(value: unknown): value is AudioAnalysis {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.transcription === "string"
    && typeof candidate.detected_issue === "string"
    && typeof candidate.severity === "string"
    && typeof candidate.summary === "string"
    && typeof candidate.recommendation === "string"
  );
}

async function analyzeTextWithOpenAI(payload: AnalyzeEmergencyRequest): Promise<AnalyzeEmergencyResult> {
  const client = new OpenAI({ apiKey: openAiApiKey });
  const response = await client.responses.create({
    model: openAiModel,
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text:
              "Eres un analista inicial de emergencias vehiculares. " +
              "Debes responder solo con datos estructurados para clasificar la urgencia.",
          },
        ],
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text:
              `Analiza esta emergencia vehicular.\n` +
              `emergency_id: ${payload.emergency_id}\n` +
              `source: ${payload.source}\n` +
              `description: ${payload.description}`,
          },
        ],
      },
    ],
    text: {
      format: {
        type: "json_schema",
        name: "vehicle_emergency_analysis",
        strict: true,
        schema: {
          type: "object",
          additionalProperties: false,
          properties: {
            classification: { type: "string" },
            priority: { type: "string" },
            summary: { type: "string" },
            recommendation: { type: "string" },
          },
          required: ["classification", "priority", "summary", "recommendation"],
        },
      },
    },
  });

  const rawText = response.output_text?.trim();
  if (!rawText) {
    throw new Error("OpenAI returned an empty structured text response");
  }

  const parsed = JSON.parse(rawText) as unknown;
  if (!isStructuredTextAnalysis(parsed)) {
    throw new Error("OpenAI returned an invalid structured text response");
  }

  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: payload.emergency_id,
    classification: parsed.classification,
    priority: parsed.priority,
    summary: parsed.summary,
    recommendation: parsed.recommendation,
  };
}

async function analyzeImageWithOpenAI(
  imageBuffer: Buffer,
  mimeType: string,
  emergencyId: number | null,
  description: string | null,
): Promise<ImageAnalyzeResponse> {
  const client = new OpenAI({ apiKey: openAiApiKey });
  const imageBase64 = imageBuffer.toString("base64");
  const response = await client.responses.create({
    model: openAiModel,
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text:
              "Eres un analista visual inicial de evidencias vehiculares. " +
              "Debes responder solo con JSON estructurado sobre daños visibles.",
          },
        ],
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text:
              `Analiza esta imagen de evidencia vehicular.\n` +
              `emergency_id: ${emergencyId ?? "null"}\n` +
              `description: ${description ?? ""}`,
          },
          {
            type: "input_image",
            image_url: `data:${mimeType};base64,${imageBase64}`,
            detail: "auto",
          },
        ],
      },
    ],
    text: {
      format: {
        type: "json_schema",
        name: "vehicle_image_analysis",
        strict: true,
        schema: {
          type: "object",
          additionalProperties: false,
          properties: {
            damage_detected: { type: "boolean" },
            severity: { type: "string" },
            summary: { type: "string" },
            recommendation: { type: "string" },
          },
          required: ["damage_detected", "severity", "summary", "recommendation"],
        },
      },
    },
  });

  const rawText = response.output_text?.trim();
  if (!rawText) {
    throw new Error("OpenAI returned an empty structured image response");
  }

  const parsed = JSON.parse(rawText) as unknown;
  if (!isImageAnalysis(parsed)) {
    throw new Error("OpenAI returned an invalid structured image response");
  }

  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: emergencyId,
    image_analysis: parsed,
  };
}

async function analyzeAudioWithOpenAI(
  file: Express.Multer.File,
  emergencyId: number,
  description: string,
): Promise<AudioAnalyzeResponse> {
  const client = new OpenAI({ apiKey: openAiApiKey });
  const audioBytes = new Uint8Array(file.buffer);
  const transcription = await client.audio.transcriptions.create({
    file: new File([audioBytes], file.originalname, {
      type: file.mimetype || "application/octet-stream",
    }),
    model: openAiTranscriptionModel,
  });

  const transcribedText = transcription.text?.trim();
  if (!transcribedText) {
    throw new Error("OpenAI transcription returned empty text");
  }

  const response = await client.responses.create({
    model: openAiModel,
    input: [
      {
        role: "system",
        content: [
          {
            type: "input_text",
            text:
              "Eres un analista inicial de audios de emergencias vehiculares. " +
              "Debes responder solo JSON estructurado.",
          },
        ],
      },
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text:
              `Analiza el siguiente audio transcrito.\n` +
              `emergency_id: ${emergencyId}\n` +
              `description: ${description || "sin descripcion adicional"}\n` +
              `transcription: ${transcribedText}`,
          },
        ],
      },
    ],
    text: {
      format: {
        type: "json_schema",
        name: "vehicle_audio_analysis",
        strict: true,
        schema: {
          type: "object",
          additionalProperties: false,
          properties: {
            transcription: { type: "string" },
            detected_issue: { type: "string" },
            severity: { type: "string" },
            summary: { type: "string" },
            recommendation: { type: "string" },
          },
          required: [
            "transcription",
            "detected_issue",
            "severity",
            "summary",
            "recommendation",
          ],
        },
      },
    },
  });

  const rawText = response.output_text?.trim();
  if (!rawText) {
    throw new Error("OpenAI returned an empty audio analysis response");
  }

  const parsed = JSON.parse(rawText) as unknown;
  if (!isAudioAnalysis(parsed)) {
    throw new Error("OpenAI returned an invalid audio analysis response");
  }

  return {
    status: "ok",
    service: "ms-ia-multimedia",
    emergency_id: emergencyId,
    audio_analysis: parsed,
  };
}

function parseOptionalEmergencyId(value: unknown): number | null {
  if (typeof value !== "string" || value.trim() === "") {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return null;
  }

  return parsed;
}

function parseEmergencyId(value: unknown): number {
  const parsed = Number(value ?? 1);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 1;
  }

  return Math.trunc(parsed);
}

app.get("/health", (_request, response) => {
  response.json({
    status: "ok",
    service: "ms-ia-multimedia",
  });
});

app.get("/metrics", async (_request, response) => {
  response.set("Content-Type", metricsRegistry.contentType);
  response.send(await metricsRegistry.metrics());
});

app.post("/analyze/emergency", async (request, response) => {
  if (!isAnalyzeEmergencyRequest(request.body)) {
    response.status(400).json({ detail: "Payload invalido" });
    return;
  }

  const payload: AnalyzeEmergencyRequest = {
    emergency_id: request.body.emergency_id,
    description: request.body.description.trim(),
    source: request.body.source.trim(),
  };

  if (!openAiApiKey) {
    response.json(buildFallbackTextResponse(payload));
    return;
  }

  try {
    const analysis = await analyzeTextWithOpenAI(payload);
    response.json(analysis);
  } catch (error) {
    console.error("OpenAI text analysis failed, using fallback:", error);
    response.json(buildFallbackTextResponse(payload));
  }
});

app.post("/evidence/upload-test", evidenceUpload.single("file"), async (request, response) => {
  const file = request.file;

  if (!file) {
    response.status(400).json({ detail: "El campo file es obligatorio" });
    return;
  }

  const safeName = path.basename(file.originalname).replace(/[^a-zA-Z0-9._-]/g, "_");
  const objectKey = `${new Date().toISOString().slice(0, 10)}/${randomUUID()}-${safeName}`;

  try {
    await s3Client.send(
      new PutObjectCommand({
        Bucket: s3Bucket,
        Key: objectKey,
        Body: file.buffer,
        ContentType: file.mimetype || "application/octet-stream",
      }),
    );
  } catch (error) {
    console.error("MinIO upload failed:", error);
    response.status(502).json({ detail: "No se pudo subir el archivo a MinIO" });
    return;
  }

  response.json({
    status: "ok",
    service: "ms-ia-multimedia",
    bucket: s3Bucket,
    object_key: objectKey,
    filename: file.originalname,
    content_type: file.mimetype || "application/octet-stream",
    size_bytes: file.size,
  });
});

app.post("/analyze/image-test", imageUpload.single("file"), async (request, response) => {
  const file = request.file;
  if (!file) {
    response.status(400).json({ detail: "El campo file es obligatorio" });
    return;
  }

  if (!allowedImageTypes.has(file.mimetype)) {
    response.status(400).json({ detail: "Tipo de archivo no permitido" });
    return;
  }

  const emergencyId = parseOptionalEmergencyId(request.body?.emergency_id);
  const description = typeof request.body?.description === "string"
    ? request.body.description.trim() || null
    : null;

  if (!openAiApiKey) {
    response.json(buildFallbackImageResponse(emergencyId));
    return;
  }

  try {
    const analysis = await analyzeImageWithOpenAI(file.buffer, file.mimetype, emergencyId, description);
    response.json(analysis);
  } catch (error) {
    console.error("OpenAI image analysis failed, using fallback:", error);
    response.json(buildFallbackImageResponse(emergencyId));
  }
});

app.post("/analyze/audio-test", audioUpload.single("file"), async (request, response) => {
  const file = request.file;
  const emergencyId = parseEmergencyId(request.body?.emergency_id);
  const description =
    typeof request.body?.description === "string" ? request.body.description.trim() : "";

  if (!file) {
    response.status(400).json({ detail: "El campo file es obligatorio" });
    return;
  }

  if (!allowedAudioTypes.has(file.mimetype)) {
    response.status(400).json({ detail: "Tipo de archivo no permitido" });
    return;
  }

  if (!openAiApiKey) {
    response.json(buildFallbackAudioResponse(emergencyId));
    return;
  }

  try {
    const analysis = await analyzeAudioWithOpenAI(file, emergencyId, description);
    response.json(analysis);
  } catch (error) {
    console.error("OpenAI audio analysis failed, using fallback:", error);
    response.json(buildFallbackAudioResponse(emergencyId));
  }
});

async function startConsumer(): Promise<void> {
  try {
    const connection = await amqp.connect(rabbitmqUrl);
    const channel = await connection.createChannel();
    await channel.assertQueue(analysisQueue, { durable: true });

    console.log(`RabbitMQ consumer connected to ${analysisQueue}`);

    await channel.consume(analysisQueue, (message: ConsumeMessage | null) => {
      if (!message) {
        return;
      }

      console.log(`Consumed message from ${analysisQueue}: ${message.content.toString("utf-8")}`);
      channel.ack(message);
    });

    connection.on("close", () => {
      console.warn("RabbitMQ connection closed. Retrying consumer in 5 seconds.");
      setTimeout(() => {
        void startConsumer();
      }, 5000);
    });

    connection.on("error", (error: Error) => {
      console.error("RabbitMQ connection error:", error);
    });
  } catch (error) {
    console.error("RabbitMQ consumer startup failed. Retrying in 5 seconds.", error);
    setTimeout(() => {
      void startConsumer();
    }, 5000);
  }
}

app.use((error: unknown, _request: express.Request, response: express.Response, _next: express.NextFunction) => {
  if (error instanceof multer.MulterError && error.code === "LIMIT_FILE_SIZE") {
    response.status(400).json({ detail: "El archivo supera el tamaño máximo permitido" });
    return;
  }

  console.error("Unhandled error:", error);
  response.status(500).json({ detail: "Error interno controlado" });
});

app.listen(port, () => {
  console.log(`ms-ia-multimedia listening on port ${port}`);
  void startConsumer();
});
