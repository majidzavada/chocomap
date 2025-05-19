// Calendar Configuration
const calendarConfig = {
    initialView: 'dayGridMonth',
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    buttonText: {
        today: 'Today',
        month: 'Month',
        week: 'Week',
        day: 'Day'
    },
    eventTimeFormat: {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    },
    slotMinTime: '06:00:00',
    slotMaxTime: '20:00:00',
    allDaySlot: false,
    slotDuration: '00:30:00',
    snapDuration: '00:15:00',
    nowIndicator: true,
    businessHours: {
        daysOfWeek: [1, 2, 3, 4, 5],
        startTime: '08:00',
        endTime: '18:00'
    }
};

// Event Colors
const eventColors = {
    delivery: {
        background: '#007bff',
        border: '#0056b3'
    },
    pickup: {
        background: '#28a745',
        border: '#1e7e34'
    },
    return: {
        background: '#dc3545',
        border: '#bd2130'
    },
    maintenance: {
        background: '#ffc107',
        border: '#d39e00'
    }
};

// Calendar Class
class DeliveryCalendar {
    constructor(elementId, options = {}) {
        this.elementId = elementId;
        this.options = { ...calendarConfig, ...options };
        this.calendar = null;
        this.events = new Map();
    }

    init() {
        const calendarElement = document.getElementById(this.elementId);
        if (!calendarElement) return null;

        this.calendar = new FullCalendar.Calendar(calendarElement, {
            ...this.options,
            eventClick: this.handleEventClick.bind(this),
            eventDrop: this.handleEventDrop.bind(this),
            eventResize: this.handleEventResize.bind(this),
            select: this.handleDateSelect.bind(this)
        });

        this.calendar.render();
        return this.calendar;
    }

    addEvent(event) {
        const eventWithColor = {
            ...event,
            backgroundColor: eventColors[event.type]?.background || '#6c757d',
            borderColor: eventColors[event.type]?.border || '#545b62'
        };

        this.calendar.addEvent(eventWithColor);
        this.events.set(event.id, event);
    }

    updateEvent(eventId, changes) {
        const event = this.calendar.getEventById(eventId);
        if (event) {
            event.setProp('title', changes.title || event.title);
            event.setStart(changes.start || event.start);
            event.setEnd(changes.end || event.end);
            event.setAllDay(changes.allDay || event.allDay);
            
            if (changes.type) {
                event.setProp('backgroundColor', eventColors[changes.type].background);
                event.setProp('borderColor', eventColors[changes.type].border);
            }
        }
    }

    removeEvent(eventId) {
        const event = this.calendar.getEventById(eventId);
        if (event) {
            event.remove();
            this.events.delete(eventId);
        }
    }

    clearEvents() {
        this.calendar.removeAllEvents();
        this.events.clear();
    }

    handleEventClick(info) {
        const event = this.events.get(info.event.id);
        if (event && this.options.onEventClick) {
            this.options.onEventClick(event);
        }
    }

    handleEventDrop(info) {
        const event = this.events.get(info.event.id);
        if (event && this.options.onEventDrop) {
            this.options.onEventDrop({
                ...event,
                start: info.event.start,
                end: info.event.end
            });
        }
    }

    handleEventResize(info) {
        const event = this.events.get(info.event.id);
        if (event && this.options.onEventResize) {
            this.options.onEventResize({
                ...event,
                start: info.event.start,
                end: info.event.end
            });
        }
    }

    handleDateSelect(info) {
        if (this.options.onDateSelect) {
            this.options.onDateSelect({
                start: info.start,
                end: info.end,
                allDay: info.allDay
            });
        }
    }

    getEvents(start, end) {
        return this.calendar.getEvents().filter(event => {
            const eventStart = event.start;
            const eventEnd = event.end || eventStart;
            return (eventStart >= start && eventStart <= end) ||
                   (eventEnd >= start && eventEnd <= end) ||
                   (eventStart <= start && eventEnd >= end);
        });
    }

    setView(view) {
        this.calendar.changeView(view);
    }

    today() {
        this.calendar.today();
    }

    prev() {
        this.calendar.prev();
    }

    next() {
        this.calendar.next();
    }
}

// Export
window.DeliveryCalendar = DeliveryCalendar; 