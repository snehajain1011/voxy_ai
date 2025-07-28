import { auth } from "~/server/auth";
import { db } from "~/server/db";
import { getPresignedUrl } from "~/lib/s3";
import { ServiceType } from "~/types/services";

export type HistoryItem = {
  id: string;
  title: string;
  voice: string | null;
  audioUrl: string | null;
  time: string;
  date: string;
  service: ServiceType;
};

export async function getHistoryItems(
  service: ServiceType,
): Promise<HistoryItem[]> {
  const session = await auth();

  if (!session?.user.id) {
    return [];
  }

  try {
    const audioClips = await db.generatedAudioClip.findMany({
      where: {
        userId: session.user.id,
        s3Key: { not: null },
        service: service,
      },
      orderBy: {
        createdAt: "desc",
      },
      take: 10,
      select: {
        id: true,
        text: true,
        voice: true,
        s3Key: true,
        createdAt: true,
        service: true,
      },
    });

    // Transform DB results to history items
    const historyItems = await Promise.all(
      audioClips.map(async (clip) => {
        let title = "Generated clip";
        if (clip.service === "seedvc") {
          title = "Voice conversion to " + clip.voice;
        } else if (clip.text !== null) {
          // Generate title from text
          title =
            clip.text.length > 50
              ? `${clip.text.substring(0, 50)}...`
              : clip.text;
        }

        // Get URL from S3 key
        const audioUrl = clip.s3Key
          ? await getPresignedUrl({ key: clip.s3Key })
          : null;

        // Format date and time
        const createdAt = new Date(clip.createdAt);
        const date = createdAt.toLocaleDateString();
        const time = createdAt.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });

        return {
          id: clip.id,
          title,
          voice: clip.voice,
          audioUrl,
          date,
          time,
          service,
        };
      }),
    );

    return historyItems;
  } catch (error) {
    console.error("Error fetching history items:", error);
    return [];
  }
}
