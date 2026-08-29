import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  format,
  parseISO,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
  isToday,
} from "date-fns";
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Clock, ArrowRight } from "lucide-react";
import { deadlinesApi, type Deadline } from "../api/deadlines";
import { getDeadlineUrgency } from "../utils/urgency";

export function Calendar() {
  const navigate = useNavigate();
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState(new Date());

  const { data: deadlines = [], isLoading } = useQuery({
    queryKey: ["deadlines", "all"],
    queryFn: () => deadlinesApi.list(),
  });

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(monthStart);
  const calendarStart = startOfWeek(monthStart);
  const calendarEnd = endOfWeek(monthEnd);

  const days = useMemo(() => {
    return eachDayOfInterval({ start: calendarStart, end: calendarEnd });
  }, [calendarStart, calendarEnd]);

  // Group deadlines by day
  const deadlinesByDay = useMemo(() => {
    const map = new Map<string, Deadline[]>();
    deadlines.forEach((dl) => {
      try {
        const dateKey = format(parseISO(dl.due_at), "yyyy-MM-dd");
        const list = map.get(dateKey) || [];
        list.push(dl);
        map.set(dateKey, list);
      } catch {}
    });
    return map;
  }, [deadlines]);

  const selectedDateKey = format(selectedDay, "yyyy-MM-dd");
  const selectedDayDeadlines = deadlinesByDay.get(selectedDateKey) || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center shadow-glow">
            <CalendarIcon className="w-5 h-5 text-on-primary" />
          </div>
          <div>
            <h1 className="text-headline-md text-on-surface">Calendar</h1>
            <p className="text-xs text-on-surface-variant">View and schedule deadlines across the month.</p>
          </div>
        </div>

        {/* Month Switcher */}
        <div className="flex items-center gap-2 bg-surface-container rounded-xl p-1 border border-white/5">
          <button
            onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
            className="p-2 hover:bg-surface-container-high text-on-surface rounded-lg transition-premium"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-semibold text-on-surface px-3 min-w-[130px] text-center">
            {format(currentMonth, "MMMM yyyy")}
          </span>
          <button
            onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
            className="p-2 hover:bg-surface-container-high text-on-surface rounded-lg transition-premium"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar Grid (2 Cols) */}
        <div className="lg:col-span-2 bg-surface-container rounded-2xl p-5 border border-white/5">
          {/* Weekday headers */}
          <div className="grid grid-cols-7 text-center text-xs font-semibold text-on-surface-variant/70 mb-2 py-1">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div key={day}>{day}</div>
            ))}
          </div>

          {/* Days Grid */}
          <div className="grid grid-cols-7 gap-1 sm:gap-2">
            {days.map((day) => {
              const dateKey = format(day, "yyyy-MM-dd");
              const dls = deadlinesByDay.get(dateKey) || [];
              const isSelected = isSameDay(day, selectedDay);
              const isCurrentMonth = isSameMonth(day, currentMonth);
              const isTodayDate = isToday(day);

              return (
                <button
                  key={dateKey}
                  onClick={() => setSelectedDay(day)}
                  className={`min-h-[64px] sm:min-h-[76px] p-2 rounded-xl border flex flex-col justify-between text-left transition-premium ${
                    isSelected
                      ? "bg-primary/15 border-primary shadow-glow"
                      : isTodayDate
                      ? "bg-surface-container-high border-primary/40"
                      : isCurrentMonth
                      ? "bg-surface-container-low border-white/5 hover:bg-surface-container-high"
                      : "bg-surface/30 border-transparent text-on-surface-variant/30 opacity-40"
                  }`}
                >
                  <span
                    className={`text-xs font-semibold ${
                      isTodayDate ? "text-primary" : isCurrentMonth ? "text-on-surface" : "text-on-surface-variant/40"
                    }`}
                  >
                    {format(day, "d")}
                  </span>

                  {/* Urgency Color Dots */}
                  {dls.length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap mt-1">
                      {dls.slice(0, 3).map((dl) => {
                        const urg = getDeadlineUrgency(dl.due_at, dl.status);
                        return <span key={dl.id} className={`w-2 h-2 rounded-full ${urg.stripeBg}`} />;
                      })}
                      {dls.length > 3 && (
                        <span className="text-[9px] font-bold text-on-surface-variant/70">+{dls.length - 3}</span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Day Sidebar */}
        <div className="bg-surface-container rounded-2xl p-5 border border-white/5 flex flex-col">
          <h2 className="text-title-md font-bold text-on-surface mb-1">
            {format(selectedDay, "EEEE, MMMM d")}
          </h2>
          <p className="text-xs text-on-surface-variant mb-4">
            {selectedDayDeadlines.length} deadline{selectedDayDeadlines.length !== 1 ? "s" : ""} on this date
          </p>

          <div className="space-y-2 flex-1 overflow-y-auto max-h-[360px]">
            {selectedDayDeadlines.length === 0 ? (
              <div className="text-center py-10 text-on-surface-variant/50 text-xs">
                No deadlines scheduled on this day.
              </div>
            ) : (
              selectedDayDeadlines.map((dl) => {
                const urg = getDeadlineUrgency(dl.due_at, dl.status);
                return (
                  <div
                    key={dl.id}
                    onClick={() => navigate(`/deadlines/${dl.id}`)}
                    className={`p-3 rounded-xl bg-surface-container-high border ${urg.cardBorder} cursor-pointer card-hover group`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs font-semibold text-on-surface group-hover:text-primary transition-premium truncate flex-1">
                        {dl.title}
                      </p>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-md ${urg.badgeBg} ${urg.badgeText}`}>
                        {format(parseISO(dl.due_at), "h:mm a")}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
