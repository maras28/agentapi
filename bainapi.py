import aiohttp
import asyncio
import json


async def send_post_request(url, payload):
    """
    Send a POST request to the specified URL with a JSON payload.
    
    Args:
        url (str): The URL to send the POST request to.
        payload (dict): The JSON payload to send.
        
    Returns:
        dict: The JSON response from the server.
    """
    # Create TCP connector with increased max_headers size (default is 8190 bytes)
    tcp_connector = aiohttp.TCPConnector(force_close=True)
      # Create client session with the custom connector and increased max_headers
    async with aiohttp.ClientSession(
        connector=tcp_connector, 
        headers={"Content-Type": "application/json"},
        max_headers=32768  # Increased from default 8190 bytes to 32KB
    ) as session:
        try:
            async with session.post(url, json=payload) as response:
                # Check if the request was successful
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Request failed with status code: {response.status}")
                    print(f"Response text: {await response.text()}")
                    return {
                        "status": "error",
                        "status_code": response.status,
                        "message": await response.text()
                    }
        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


async def main():
    # Sample endpoint and payload
    url = "http://togg-genai.germanywestcentral.cloudapp.azure.com/staging/api/api/v1/chat_response/streaming"
    
    # Sample JSON payload
    payload = {
        "question": "Hotels in New York?"
    }
    
    # Send the POST request
    response = await send_post_request(url, payload)
    
    # Print the response
    print("Response:")
    print(json.dumps(response, indent=4))


# To run the code from command line
if __name__ == "__main__":
    asyncio.run(main())