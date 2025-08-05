# Search experts based on an unstructured solicitation and role
This feature should create a new POST endpoint called /api/experts/search to search experts using a custom "knowledge-based" algorithm. It should work like this:

1. Use an LLM with function-calling to get the top attributes for the input text. Use the config.py to see which attribute types to query, and then get the top 1-3 attributes for each type listed. 
2. Create a joined aggregate query that does the following:
    Creates an exponential score for each experience in the following structure 1.1^n where n is the number of matching attributes. Multiply this score by the number of days from the start date of the experience to the end. Then remove .25 * the number of days from the end_date of the experience to now, to weight for more recent eperiences. This score is called an experience knowledge score
    Next, aggregate by expert and sum the total experience knowledge scores for each expert. 
    Lastly, order the list of experts in decending order by each expert's sum knowledge score.
3. Return the list of experts in decending order. 