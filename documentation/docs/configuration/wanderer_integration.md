# Wanderer Integration

[Wanderer](https://wanderer.to) is a self-hosted trail database. Integrating Wanderer with AdventureLog allows you to import trails directly into your locations, making it easier to plan and track your outdoor adventures.

## Wanderer Integration Setup

1. Navigate to the AdventureLog settings page.
2. Click on the **Integrations** tab.
3. Find the **Wanderer** section and input the URL of your Wanderer instance, your username, and password.
4. Click the **Connect Account** button to authenticate with your Wanderer instance.

### Important Notes

1. The URL to the Wanderer server must be accessible from the AdventureLog server. This means values like `localhost` or `127.0.0.1` will likely cause some issues.
2. AdventureLog **does not store your Wanderer credentials**. They are only used to fetch an authorization token for the Wanderer API. This token will last for around 2 weeks before needing to be refreshed. Using the token refreshes the token for another 2 weeks. Should the token expire, you will need to re-enter your credentials in the AdventureLog settings page.

## Importing Wanderer Trails

1. Open the create/edit location popup in AdventureLog.
2. Naviage to the **Media** tab and scroll down to the **Trail Managment** section.
3. Click the **Add Wanderer Trail** button.
4. A search input will appear. Type in the name of the trail you want to import.
5. Select the desired trail from the search results and click the link icon to import it into your location.
6. The imported trail will be added to your location's trails list, and you can view its details, including distance, elevation gain, and more.

Enjoy exploring new trails with Wanderer and AdventureLog! If you encounter any issues or have questions about the integration, feel free to reach out to the AdventureLog community!
