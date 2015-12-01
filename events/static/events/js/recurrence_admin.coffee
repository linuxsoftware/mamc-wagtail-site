#---------------------------------------------------------------------------
# Recurrence Widget
#---------------------------------------------------------------------------

class RecurrenceWidget
    constructor: (widgetId) ->
        ourDiv = $("##{widgetId}")
        @our = ourDiv.find.bind(ourDiv)
        @_init()
        return

    _init: () ->
        showAdvanced = @_hasAdvanced()
        @our(".ev-show-advanced-cbx").prop("checked", showAdvanced)
        @our(".ev-advanced-repeat").toggle(showAdvanced)
        freq = @our(".ev-freq-choice > select").val()
        @_freqChanged(freq)

    _hasAdvanced: () ->
        interval = @our(".ev-interval-num > input").val()
        if interval and parseInt(interval) > 1
            return true
        weekdaysTicked = @our(".ev-weekdays :checkbox:checked").map ->
            return this.value
        .get()
        if weekdaysTicked.length > 1
            return true
        dtstart = new Date(@our(".ev-start-date > input").val())
        weekday = (dtstart.getDay() + 6) % 7  # convert from Sun=0 to Mon=0
        if weekdaysTicked.length == 1 and parseInt(weekdaysTicked[0]) != weekday
            return true
        ordChoice = @our(".ev-ord-choice > select").val()
        if parseInt(ordChoice) != 101
            return true
        dayChoice = @our(".ev-day-choice > select").val()
        if parseInt(dayChoice) != 200
            return true
        return false

    _clearAdvanced: () ->
        @our(".ev-interval-num > input").val(1)
        @our(".ev-weekdays :checkbox").prop("checked", false)
        dtstart = new Date(@our(".ev-start-date > input").val())
        weekday = (dtstart.getDay() + 6) % 7  # convert from Sun=0 to Mon=0
        @our(".ev-weekdays :checkbox[value=#{weekday}]").prop("checked", true)
        @our(".ev-ord-choice > select").val(101)
        @our(".ev-day-choice > select").val(200)
        @our(".ev-month-choice > select").val(dtstart.getMonth() + 1)
        return

    enable: () ->
        @_enableShowAdvanced()
        @_enableStartDateChange()
        @_enableFreqChange()
        return

    _enableShowAdvanced: () ->
        @our(".ev-show-advanced-cbx").click (ev) =>
            if $(ev.target).prop("checked")
                @our(".ev-advanced-repeat").show()
            else
                @our(".ev-advanced-repeat").hide()
                @_clearAdvanced()
            return true
        return

    _enableStartDateChange: () ->
        @our(".ev-start-date > input, .ev-").change (ev) =>
            showAdvanced = @our(".ev-show-advanced-cbx").prop("checked")
            if not showAdvanced
                @_clearAdvanced()
            return false
        return

    _enableFreqChange: () ->
        @our(".ev-freq-choice > select").change (ev) =>
            @_freqChanged($(ev.target).val())
            @_clearAdvanced()
            return false
        return

    _freqChanged: (freq) ->
        vis = [false, false, false]
        units = ""
        switch parseInt(freq)
            when 3
                vis = [false, false, false]
                units = "Day(s)"
            when 2
                vis = [true,  false, false]
                units = "Week(s)"
            when 1
                vis = [false, true,  false]
                units = "Month(s)"
            when 0
                vis = [false, true, true]
                units = "Year(s)"
        @our(".ev-advanced-weekly-repeat").toggle(vis[0])
        @our(".ev-advanced-monthly-repeat").toggle(vis[1])
        @our(".ev-advanced-yearly-repeat").toggle(vis[2])
        @our(".ev-interval-units").text(units)
        return

@initRecurrenceWidget = (id) ->
    widget = new RecurrenceWidget(id)
    widget.enable()
    return

@initExceptionDateChooser = (id, validDates) ->
    dtpOpts =
        onGenerate: (ct) ->
            future = new Date()
            future.setDate(future.getDate()+157)
            future.setDate(1)
            console.log(future)
            if validDates != -1 and ct < future
                $(this).find('td.xdsoft_date').addClass('xdsoft_disabled')
                for yyyymmdd in validDates
                    yyyy = parseInt(yyyymmdd[0...4])
                    mm   = parseInt(yyyymmdd[4...6]) - 1
                    dd   = parseInt(yyyymmdd[6...8])
                    $(this).find("td.xdsoft_date[data-year=#{yyyy}][data-month=#{mm}][data-date=#{dd}]")
                           .removeClass('xdsoft_disabled')
        closeOnDateSelect: true
        timepicker:        false
        scrollInput:       false
        format:            'Y-m-d'
        dayOfWeekStart:    0    # Keep this the same as Recurrence
#        weekends: ['2015/11/05']
#        disabledDates: ['2015/11/04', '2015/11/03']
    if window.dateTimePickerTranslations
        dtpOpts['i18n'] = lang: window.dateTimePickerTranslations
        dtpOpts['lang'] = 'lang'
    $('#' + id).datetimepicker(dtpOpts)
