// Some Constant Vars being used across the script
// Probably need a better way to manage this state though
// @TODO : Fix This global variable

var notification_ws
var notifCount = 0
var inRestart = false


const serviceLookup = {
  spatial: "spatialdatasetservice",
  dataset: "datasetservice",
  wps: "webprocessingservice",
  persistent: "persistentstoreservice"
}

const reloadCacheRefresh = () => {
  notification_ws.send(
    JSON.stringify({
      data: {},
      type: `clear_conda_channel_cache`
    })
  )
  // Refresh Page
  location.reload()
}

function resetInstallStatus() {
  if (installData) {
    installData = {}
  }
  installRunning = false
}

function setServerOffline() {
  $("#offline-modal").modal("show")
  $("#overlay").show()
  $("#serverStatusOnline").hide()
  $("#serverStatusOffline").show()
}

function setServerOnline() {
  $("#overlay").hide()
  $("#offline-modal").modal("hide")
  $("#serverStatusOnline").show()
  $("#serverStatusOffline").hide()
  // Check for any pending updates and resume processing
  if (installRunning) {
    // Send WS request
    notification_ws.send(
      JSON.stringify({
        data: installData,
        type: "continueAfterInstall"
      })
    )
  }
}

function getParameterByName(name, url) {
  if (!url) return null
  name = name.replace(/[\[\]]/g, "\\$&")
  var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
    results = regex.exec(url)
  if (!results) return null
  if (!results[2]) return ""
  return decodeURIComponent(results[2].replace(/\+/g, " "))
}

const hideLoader = (modal = "notification") => {
  $(`#installLoaderEllipsis`).hide()
}

const showLoader = (modal = "notification") => {
  $(`#installLoaderEllipsis`).show()
  $("#mainCancel").hide()
}

const sendNotification = (message, n_content) => {
  notifCount = notifCount + 1
  let new_element = `<div style="display: none;" id="install_notif_${notifCount}">${message}</div>`
  if (message == "install_complete") {
    new_element = `<div style="display: none;" id="install_notif_${notifCount}">Install Complete. Restarting Server for changes to take effect.</div>`
    inRestart = true
    notification_ws.send(
      JSON.stringify({
        data: { ...installData, restart_type: "install" },
        type: `restart_server`
      })
    )
    resetInstallStatus()
  }
  if (message == "Uninstall completed. Restarting server...") {
    inRestart = true
    notification_ws.send(
      JSON.stringify({
        data: { ...uninstallData, restart_type: "uninstall" },
        type: `restart_server`
      })
    )
  }
  n_content.append(new_element)
  $(`#install_notif_${notifCount}`).show("fast")
}

function startWS(websocketServerLocation, n_content) {
  notification_ws = new WebSocket(websocketServerLocation)
  notification_ws.onopen = () => {
    console.log("WebSocket is Open")
    if (inRestart) {
      inRestart = false

      if ("name" in uninstallData) {
        // Coming back from an uninstall restart
        sendNotification(
          "Server restart completed successfully",
          $("#uninstallNotices")
        )

        $("#uninstallLoaderEllipsis").hide()
        $("#doneUninstallButton").show()
      } else {
        hideLoader()
        sendNotification("Server restart completed successfully", n_content)
        $("#goToAppButton").show()
        $("#doneInstallButton").show()
        // Hide Cancel Button
        $("#mainCancel").hide()
      }
    }
    // Check if we have any updateData
    if ("name" in updateData) {
      // clear out updateData
      updateData = {}
      sendNotification(
        "Server restart completed successfully",
        $("#update-notices")
      )
      $("#update-loader").hide()
      $("#done-update-button").show()
    }
    setServerOnline()
  }

  notification_ws.onmessage = function(e) {
    let data = JSON.parse(e.data)
    let content = n_content

    if (typeof data.message == "string") {
      // It's normal string
      sendNotification(data.message, content)
      return false
    } else {
      // Found an object?
      // Check if we have a function to call
      let helper = settingsHelper

      if ("target" in data.message) {
        content = $(`#${data.message.target}`)
        return sendNotification(data.message.message, content)
      }

      if ("helper" in data.message) {
        if (data.message["helper"] == "addModalHelper") {
          helper = addModalHelper
          content = $("#statusMessagesAdd")
        }
      }
      if ("jsHelperFunction" in data.message) {
        helper[data.message["jsHelperFunction"]](
          data.message.data,
          content,
          data.message,
          notification_ws
        )
      } else {
        console.log("Undefined jsHelperFunction in JSON WebSocket call")
      }
    }
  }

  notification_ws.onclose = function() {
    setServerOffline()
    // Try to reconnect in 1 second
    setTimeout(function() {
      startWS(websocketServerLocation, n_content)
    }, 1000)
  }
}
