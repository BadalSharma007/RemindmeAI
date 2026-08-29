import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { format, parseISO, formatDistanceToNow } from "date-fns";
import { Search as SearchIcon, CalendarClock, Clock, Sparkles, ArrowRight, X } from "lucide-react";
import { deadlinesApi } from "../api/deadlines";
import { getDeadlineUrgency } from "../utils/urgency";

export function Search() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const { data: deadlines = [], isLoading } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
  });

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    return deadlines.filter(dl =>
      dl.title.toLowerCase().includes(q) ||
      (dl.source_text && dl.source_text.toLowerCase().includes(q))
    );
  }, [query, deadlines]);

  const statusColors: Record<string, string> = {
    pending: "text-amber-400 bg-amber-500/10",
    reminded: "text-primary bg-primary/10",
    completed: "text-green-400 bg-green-500/10",
    dismissed: "text-on-surface-variant/60 bg-on-surface-variant/10",
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <SearchIcon className="w-5 h-5 text-primary" />
          <h1 className="text-headline-md text-on-surface">Search</h1>
        </div>
        <p className="text-body-md text-on-surface-variant ml-8">Find deadlines by title or content.</p>
      </div>

      {/* Search Input */}
      <div className="relative mb-6">
        <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-on-surface-variant/50" />
        <input
          id="search-input"
          type="text"
          autoFocus
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search deadlines..."
          className="w-full bg-surface-container text-on-surface rounded-2xl pl-12 pr-12 py-4 text-base ghost-border ghost-border-focus transition-premium placeholder:text-on-surface-variant/40 border border-white/5"
        />
        {query && (
          <button onClick={() => setQuery("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-surface-container-high text-on-surface-variant transition-premium">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Results */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-20 rounded-xl" />)}
        </div>
      )}

      {!isLoading && !query && (
        <div className="text-center py-12">
          <SearchIcon className="w-12 h-12 text-on-surface-variant/20 mx-auto mb-4" />
          <p className="text-on-surface-variant text-sm">Start typing to search your deadlines.</p>
          <p className="text-xs text-on-surface-variant/40 mt-2">{deadlines.length} deadline{deadlines.length !== 1 ? "s" : ""} available</p>
        </div>
      )}

      {!isLoading && query && results.length === 0 && (
        <div className="text-center py-12">
          <CalendarClock className="w-12 h-12 text-on-surface-variant/20 mx-auto mb-4" />
          <p className="text-on-surface-variant text-sm font-medium">No deadlines matching "{query}"</p>
          <p className="text-xs text-on-surface-variant/40 mt-2">Try a different search term.</p>
        </div>
      )}

      {!isLoading && results.length > 0 && (
        <div>
          <p className="text-xs text-on-surface-variant/50 mb-3">{results.length} result{results.length !== 1 ? "s" : ""} for "{query}"</p>
          <div className="space-y-3">
            {results.map((dl, idx) => {
              const urgency = getDeadlineUrgency(dl.due_at, dl.status);
              const isAI = dl.source_text && dl.source_text !== "Manual entry" && dl.confidence_score < 1.0;
              return (
                <div
                  key={dl.id}
                  onClick={() => navigate(`/deadlines/${dl.id}`)}
                  className={`bg-surface-container rounded-xl p-5 card-hover cursor-pointer group border ${urgency.cardBorder} animate-slide-up relative overflow-hidden`}
                  style={{ animationDelay: `${idx * 40}ms` }}
                >
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${urgency.stripeBg} rounded-l-xl`} />

                  <div className="flex items-start justify-between gap-4 pl-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                        <p className="text-on-surface font-semibold group-hover:text-primary transition-premium truncate">
                          {dl.title}
                        </p>
                        
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${urgency.badgeBg} ${urgency.badgeText} ${urgency.badgeBorder}`}>
                          {urgency.label}
                        </span>

                        {isAI && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-primary/10 text-primary flex items-center gap-1 shrink-0">
                            <Sparkles className="w-2.5 h-2.5" />AI
                          </span>
                        )}
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${statusColors[dl.status] ?? statusColors.pending}`}>
                          {dl.status}
                        </span>
                      </div>
                      {dl.source_text && dl.source_text !== "Manual entry" && (
                        <p className="text-xs text-on-surface-variant/50 truncate mb-2">{dl.source_text}</p>
                      )}
                      <div className="flex items-center gap-1.5">
                        <Clock className={`w-3.5 h-3.5 ${urgency.iconColor}`} />
                        <span className={`text-xs ${urgency.badgeText} font-medium`}>
                          {format(parseISO(dl.due_at), "MMM d, yyyy · h:mm a")}
                          <span className="ml-1 text-on-surface-variant/60 font-normal">({formatDistanceToNow(parseISO(dl.due_at), { addSuffix: true })})</span>
                        </span>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-on-surface-variant/40 group-hover:text-primary transition-premium shrink-0 mt-1" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
