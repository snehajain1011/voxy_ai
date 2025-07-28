"use client";

import {
  IoDownloadOutline,
  IoPlayOutline,
  IoVolumeHighOutline,
} from "react-icons/io5";
import { HistoryItem } from "~/lib/history";
import { useAudioStore } from "~/stores/audio-store";

export function HistoryList({ historyItems }: { historyItems: HistoryItem[] }) {
  const { playAudio } = useAudioStore();

  const groupedItems = historyItems.reduce(
    (groups: Record<string, typeof historyItems>, item) => {
      const date = item.date;
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(item);
      return groups;
    },
    {},
  );

  return (
    <>
      <style jsx>{`
        @keyframes gradientMove {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }
      `}</style>

      <div className="relative flex h-full w-full flex-col items-center">
        <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 transform">
          <div
            className="h-[200px] w-full bg-gradient-to-r from-teal-300 via-blue-300 to-teal-300 opacity-20 blur-[70px]"
            style={{ animation: "gradientMove 20s ease infinite" }}
          ></div>
        </div>

        {/* Content */}
        <div className="relative z-10 flex h-full w-full flex-col items-center md:pt-10">
          <div className="w-full max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
            <div className="mb-4">
              <h2 className="text-lg font-medium">Recent Sound Effects</h2>
            </div>

            {historyItems.length > 0 ? (
              <div className="mt-6">
                {Object.entries(groupedItems).map(([date, items]) => (
                  <div key={date} className="mb-6">
                    <div className="mb-3">
                      <span className="text-xs font-medium text-gray-500">
                        {date}
                      </span>
                    </div>
                    <div className="flex flex-col gap-3">
                      {items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between gap-2 rounded-lg border border-gray-100 bg-white p-4 hover:bg-gray-50 md:gap-0"
                        >
                          {/* Left side */}
                          <div className="flex min-w-0 flex-1 items-center">
                            <div className="mr-4 flex-shrink-0">
                              <IoVolumeHighOutline className="h-5 w-5 text-gray-500" />
                            </div>
                            <p className="break-words text-xs font-medium text-gray-800 md:truncate md:text-sm">
                              <span className="block sm:hidden">
                                {item.title.length > 15
                                  ? `${item.title.substring(0, 15)}...`
                                  : item.title}
                              </span>
                              <span className="hidden sm:block">
                                {item.title}
                              </span>
                            </p>
                          </div>

                          {/* Right side */}
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-gray-500">
                              {item.time}
                            </span>

                            <div className="flex gap-2">
                              <button
                                onClick={() => {
                                  if (item.audioUrl) {
                                    playAudio({
                                      id: item.id.toString(),
                                      title: item.title,
                                      voice: item.voice || "",
                                      audioUrl: item.audioUrl,
                                      service: item.service,
                                    });
                                  }
                                }}
                                className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200"
                              >
                                <IoPlayOutline className="h-4 w-4" />
                              </button>
                              <button
                                onClick={() => {
                                  if (item.audioUrl) {
                                    const a = document.createElement("a");
                                    a.href = item.audioUrl;
                                    a.download = `${item.title || "sound-effect"}.wav`;
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                  }
                                }}
                                className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 hover:bg-gray-200"
                              >
                                <IoDownloadOutline className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-40 items-center justify-center">
                <p className="text-center text-gray-500">
                  No sound effects generated yet
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
