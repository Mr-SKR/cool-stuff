export default {
  // The scheduled handler is invoked by Cron Triggers
  async scheduled(event, env, ctx) {
    ctx.waitUntil(checkTickets());
  },
  
  // Also allow manual triggering via HTTP for testing/debugging
  async fetch(request, env, ctx) {
    await checkTickets();
    return new Response("Ticket check executed. Check Cloudflare Worker logs or your ntfy topic!");
  }
};

async function checkTickets() {
  const url = 'https://rcbscaleapi.ticketgenie.in/ticket/eventlist/O';
  
  const headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9,hi;q=0.8',
    'authorization': 'Bearer <token>', // TODO: Replace with actual token if required
    'origin': 'https://shop.royalchallengers.com',
    'referer': 'https://shop.royalchallengers.com/',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'
  };

  try {
    const response = await fetch(url, { headers });
    if (!response.ok) {
      console.error(`HTTP error! status: ${response.status}`);
      await sendNtfyNotification('default', "Error fetching ticket information.");
      return;
    }
    
    const data = await response.json();
    
    if (data.status === "Success" && data.result && data.result.length > 0) {
      // Filter for events where the button text is exactly "BUY TICKETS"
      const availableEvents = data.result.filter(event => 
        event.event_Button_Text && event.event_Button_Text.toUpperCase() === "BUY TICKETS"
      );

      if (availableEvents.length > 0) {
        let message = "RCB Tickets Available!\n\n";
        availableEvents.forEach(e => {
          message += `${e.event_Name} (${e.event_Display_Date})\nPrice: ${e.event_Price_Range}\n\n`;
        });
        message += "Buy here: https://shop.royalchallengers.com/ticket";

        // Send to ntfy
        await sendNtfyNotification('urgent', message);
      } else {
        console.log("No events with 'BUY TICKETS' found.");
        await sendNtfyNotification('high', "No events with 'BUY TICKETS' found.");
      }
    } else {
      console.log("API returned Success but no results were found.");
    }
  } catch (error) {
    console.error("Error fetching tickets:", error);
    await sendNtfyNotification('default', "Error fetching ticket information.");
  }
}

async function sendNtfyNotification(priority, message) {
  // TODO: Change this to a unique, secret topic name
  // Anyone subscribed to this topic on ntfy.sh will receive the alert
  const ntfyTopic = 'rcb-tickets-alert-suresh-reddy-cloudflare-worker';
  
  await fetch(`https://ntfy.sh/${ntfyTopic}`, {
    method: 'POST',
    body: message,
    headers: {
      'Title': 'RCB Tickets Alert!',
      'Tags': 'cricket,ticket,warning',
      'Priority': priority
    }
  });
  console.log(`Notification sent to ntfy topic: ${ntfyTopic}`);
}
